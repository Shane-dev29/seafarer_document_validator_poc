import os
import sys
import json
import base64
import asyncio
import threading
import urllib.parse
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import requests
import websockets

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import LLM_URL, LLM_MODEL, LLM_API_KEY, GEMINI_API_KEY
from core.screencast import screencast_broadcaster
from google import genai
from orchestrator.workflow import run_seafarer_verification

WS_PORT = 8001   # WebSocket port for live browser streaming

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR = PROJECT_ROOT / "verified_reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

class MaritimeAIRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # 1. Health Endpoint
        if parsed.path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = {
                "status": "online",
                "local_model": LLM_MODEL,
                "local_url": LLM_URL,
                "gemini_available": bool(GEMINI_API_KEY),
                "screencast_ws": f"ws://127.0.0.1:{WS_PORT}/screencast"
            }
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        # 2b. Replay frames endpoint (for scrubber)
        if parsed.path == "/api/replay-frames":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            frames = screencast_broadcaster.get_all_replay_frames()
            # Only send metadata (label + index), not full base64 to save bandwidth
            frame_meta = [{"label": f["label"], "index": i} for i, f in enumerate(frames)]
            self.wfile.write(json.dumps({"frames": frame_meta, "total": len(frames)}).encode("utf-8"))
            return

        # 2. List Reports Endpoint
        if parsed.path == "/api/reports":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            reports = []
            if REPORTS_DIR.exists():
                for sub in sorted(REPORTS_DIR.iterdir(), key=os.path.getmtime, reverse=True):
                    if sub.is_dir():
                        rfile = sub / "verification_report.json"
                        if rfile.exists():
                            try:
                                with open(rfile, "r", encoding="utf-8") as f:
                                    rdata = json.load(f)
                                    reports.append({
                                        "folder_name": sub.name,
                                        "timestamp": rdata.get("timestamp"),
                                        "batch_name": rdata.get("batch_name"),
                                        "status": rdata.get("verification_status"),
                                        "profile": rdata.get("consolidated_profile")
                                    })
                            except Exception:
                                pass

            self.wfile.write(json.dumps({"reports": reports}).encode("utf-8"))
            return

        # Serve static files for everything else
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        # 1. Run Verification Pipeline Endpoint
        if parsed.path == "/api/verify-batch":
            content_type = self.headers.get("Content-Type", "")
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                # Handle JSON payload or multipart
                if "application/json" in content_type:
                    payload = json.loads(body.decode("utf-8"))
                    folder_path = payload.get("folder_path")
                    pdf_path = payload.get("pdf_path")
                    profile = payload.get("profile")
                    headless = payload.get("headless", True)
                else:
                    # Multipart upload: save files to a unique batch directory
                    boundary = content_type.split("boundary=")[-1].encode("utf-8")
                    parts = body.split(b"--" + boundary)
                    
                    import time
                    batch_id = f"batch_{int(time.time())}"
                    batch_folder = UPLOAD_DIR / batch_id
                    batch_folder.mkdir(parents=True, exist_ok=True)

                    for part in parts:
                        if b"Content-Disposition" in part and b'filename="' in part:
                            headers_part, file_bytes = part.split(b"\r\n\r\n", 1)
                            file_bytes = file_bytes.rstrip(b"\r\n")
                            
                            filename = "document.pdf"
                            header_str = headers_part.decode("utf-8", errors="ignore")
                            for line in header_str.split("\r\n"):
                                if "filename=" in line:
                                    filename = line.split('filename="')[-1].split('"')[0]

                            with open(batch_folder / filename, "wb") as f:
                                f.write(file_bytes)

                    folder_path = str(batch_folder.resolve())
                    pdf_path = None
                    profile = None
                    headless = True  # Always headless — browser streamed via WS instead

                # Reset screencast for fresh run
                screencast_broadcaster.clear()
                screencast_broadcaster.set_live(True)

                print(f"[WebAPI] Invoking LangGraph Pipeline on: {folder_path or pdf_path or profile}")
                result_state = run_seafarer_verification(
                    folder_path=folder_path,
                    pdf_path=pdf_path,
                    profile=profile,
                    headless=True,   # Always headless; screencast streams to UI
                    screencast=screencast_broadcaster
                )

                screencast_broadcaster.set_live(False)

                # Attach screenshot data URI if available
                screenshot_path = ""
                if result_state.get("verification_result"):
                    screenshot_path = result_state["verification_result"].get("screenshot_path", "")

                screenshot_b64 = ""
                if screenshot_path and Path(screenshot_path).exists():
                    with open(screenshot_path, "rb") as sf:
                        screenshot_b64 = f"data:image/png;base64,{base64.b64encode(sf.read()).decode('utf-8')}"

                response_data = {
                    "status": result_state.get("status"),
                    "batch_name": result_state.get("batch_name"),
                    "profile": result_state.get("seafarer_profile"),
                    "document_matrix": result_state.get("document_matrix"),
                    "country_resolved": result_state.get("country_resolved"),
                    "verification_result": result_state.get("verification_result"),
                    "screenshot_data_uri": screenshot_b64,
                    "audit_report_path": result_state.get("audit_report_path"),
                    "error": result_state.get("error")
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode("utf-8"))

            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"detail": str(e)}).encode("utf-8"))
            return

        # 2. Chat Endpoint
        if parsed.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            
            try:
                req = json.loads(post_data.decode("utf-8"))
                messages = req.get("messages", [])
                provider = req.get("model_provider", "local")
                system_prompt = req.get("system_prompt")
                temperature = float(req.get("temperature", 0.2))

                if provider == "gemini" and GEMINI_API_KEY:
                    client = genai.Client(api_key=GEMINI_API_KEY)
                    contents = []
                    if system_prompt:
                        contents.append(f"System: {system_prompt}\n")

                    for m in messages:
                        role = m.get("role", "user")
                        content = m.get("content", "")
                        if role == "system":
                            continue
                        if isinstance(content, str):
                            contents.append(f"{role.capitalize()}: {content}")
                        elif isinstance(content, list):
                            text_parts = []
                            for part in content:
                                if isinstance(part, dict):
                                    if part.get("type") == "text":
                                        text_parts.append(part.get("text", ""))
                                    elif part.get("type") == "image_url":
                                        url_data = part.get("image_url", {}).get("url", "")
                                        if url_data.startswith("data:"):
                                            header, encoded = url_data.split(",", 1)
                                            mime = header.split(";")[0].replace("data:", "")
                                            img_bytes = base64.b64decode(encoded)
                                            contents.append(genai.types.Part.from_bytes(data=img_bytes, mime_type=mime))
                            if text_parts:
                                contents.append(f"{role.capitalize()}: {' '.join(text_parts)}")

                    resp = client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=contents
                    )
                    reply = resp.text.strip()
                    model_used = "gemini-3.6-flash"

                else:
                    headers = {
                        "Authorization": f"Bearer {LLM_API_KEY}",
                        "Content-Type": "application/json"
                    }
                    formatted_messages = []
                    if system_prompt:
                        formatted_messages.append({"role": "system", "content": system_prompt})
                    for m in messages:
                        formatted_messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})

                    payload = {
                        "model": LLM_MODEL,
                        "messages": formatted_messages,
                        "temperature": temperature,
                        "max_tokens": 1500
                    }
                    resp = requests.post(LLM_URL, headers=headers, json=payload, timeout=90)
                    resp.raise_for_status()
                    data = resp.json()
                    reply = data["choices"][0]["message"]["content"].strip()
                    model_used = LLM_MODEL

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"response": reply, "provider": model_used}).encode("utf-8"))

            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"detail": str(e)}).encode("utf-8"))
            return

        # 3. Single Upload Endpoint
        if parsed.path == "/api/upload":
            content_type = self.headers.get("Content-Type", "")
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                boundary = content_type.split("boundary=")[-1].encode("utf-8")
                parts = body.split(b"--" + boundary)
                
                filename = "uploaded_file.png"
                file_bytes = b""
                mime = "image/png"

                for part in parts:
                    if b"Content-Disposition" in part and b'filename="' in part:
                        headers_part, file_bytes = part.split(b"\r\n\r\n", 1)
                        file_bytes = file_bytes.rstrip(b"\r\n")
                        
                        header_str = headers_part.decode("utf-8", errors="ignore")
                        for line in header_str.split("\r\n"):
                            if "filename=" in line:
                                filename = line.split('filename="')[-1].split('"')[0]
                            if "Content-Type:" in line:
                                mime = line.split("Content-Type:")[-1].strip()

                b64 = base64.b64encode(file_bytes).decode("utf-8")
                data_uri = f"data:{mime};base64,{b64}"

                save_path = UPLOAD_DIR / filename
                with open(save_path, "wb") as f:
                    f.write(file_bytes)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "filename": filename,
                    "content_type": mime,
                    "data_uri": data_uri,
                    "local_path": str(save_path)
                }).encode("utf-8"))

            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"detail": str(e)}).encode("utf-8"))
            return

        self.send_error(404, "Endpoint not found")

# ---------------------------------------------------------------------------
# WebSocket screencast server (runs on port 8001 in a daemon thread)
# ---------------------------------------------------------------------------

async def _ws_screencast_handler(websocket):
    """Handle a single WebSocket client connection for screencast streaming."""
    client_queue = screencast_broadcaster.register_client()
    print(f"[Screencast WS] Client connected: {websocket.remote_address}")
    try:
        while True:
            # Drain the client's frame queue and send
            try:
                msg = client_queue.get(timeout=0.5)
                await websocket.send(msg)
            except Exception:
                # Yield control so we can detect disconnects
                await asyncio.sleep(0.05)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        screencast_broadcaster.unregister_client(client_queue)
        print(f"[Screencast WS] Client disconnected: {websocket.remote_address}")


async def _replay_frame_handler(websocket, index: int):
    """Send a specific replay frame on demand."""
    frame = screencast_broadcaster.get_replay_frame(index)
    if frame:
        await websocket.send(json.dumps({
            "type": "replay_frame",
            "data": frame["data"],
            "label": frame["label"],
            "frame_index": index
        }))


async def _ws_router(websocket):
    """Route WebSocket connections by path."""
    path = websocket.request.path if hasattr(websocket, 'request') else getattr(websocket, 'path', '/screencast')
    if path.startswith("/replay/"):
        try:
            idx = int(path.split("/replay/")[-1])
            await _replay_frame_handler(websocket, idx)
        except ValueError:
            pass
    else:
        # Default: live screencast stream
        await _ws_screencast_handler(websocket)


def _start_ws_server(ws_port: int = WS_PORT):
    """Start the WebSocket server in its own asyncio event loop (daemon thread)."""
    async def _serve():
        host = os.environ.get("WS_HOST", "0.0.0.0")
        async with websockets.serve(_ws_router, host, ws_port):
            print(f"[Screencast WS] Server live at ws://{host}:{ws_port}")
            await asyncio.Future()   # run forever

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_serve())


# ---------------------------------------------------------------------------
# Main HTTP server
# ---------------------------------------------------------------------------

def run_server(port: int = 8000):
    host = os.environ.get("HTTP_HOST", "0.0.0.0")
    # Start WebSocket server in background daemon thread
    ws_thread = threading.Thread(target=_start_ws_server, daemon=True)
    ws_thread.start()

    server = ThreadingHTTPServer((host, port), MaritimeAIRequestHandler)
    print("\n" + "=" * 60)
    print("  MARITIME AI STUDIO WEB INTERFACE LIVE!")
    print(f"  HTTP  : http://{host}:{port}")
    print(f"  WS    : ws://{host}:{WS_PORT}/screencast  (Live Browser Stream)")
    print("=" * 60 + "\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Server] Shutting down.")
        server.server_close()

if __name__ == "__main__":
    run_server()
