import os
import sys
import json
import base64
import argparse
import requests
from pathlib import Path
from core.config import LLM_URL, LLM_MODEL, LLM_API_KEY

def encode_image_to_base64(image_path: Path) -> tuple:
    """Reads image and returns (base64_str, mime_type)."""
    suffix = image_path.suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp"
    }
    mime_type = mime_map.get(suffix, "image/jpeg")
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return encoded, mime_type

def send_chat_message(messages: list, url: str = LLM_URL, model: str = LLM_MODEL, api_key: str = LLM_API_KEY) -> str:
    """Sends chat payload to the local LiteLLM OpenAI-compatible endpoint."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 1500
    }

    response = requests.post(url, headers=headers, json=payload, timeout=90)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()

def run_interactive_chat(initial_image: str = None):
    print("=" * 65)
    print("  LOCAL MODEL INTERACTIVE CHAT & IMAGE UPLOADER")
    print("=" * 65)
    print(f"Endpoint URL : {LLM_URL}")
    print(f"Model Name   : {LLM_MODEL}")
    print("\nCommands:")
    print("  - Type your message and press Enter to chat.")
    print("  - Type `/image <path>` to attach an image to your next question.")
    print("  - Type `exit` or `quit` to end the session.")
    print("=" * 65 + "\n")

    history = [
        {"role": "system", "content": "You are a helpful AI assistant. Answer user queries accurately."}
    ]

    current_image_path = None
    if initial_image:
        p = Path(initial_image)
        if p.exists():
            current_image_path = p
            print(f"[+] Loaded initial image: {current_image_path.resolve()}\n")
        else:
            print(f"[!] Warning: Image '{initial_image}' not found.\n")

    while True:
        try:
            prompt_prefix = f"You [Image attached: {current_image_path.name}]" if current_image_path else "You"
            user_input = input(f"{prompt_prefix} > ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                print("\n[Chat] Exiting session. Goodbye!")
                break

            # Handle /image command
            if user_input.startswith("/image "):
                raw_path = user_input[7:].strip().strip('"').strip("'")
                p = Path(raw_path)
                if p.exists():
                    current_image_path = p
                    print(f"\n[+] Attached image: {current_image_path.resolve()}")
                    print("[+] Now type your question about this image below:\n")
                else:
                    print(f"\n[!] Error: File not found at '{raw_path}'\n")
                continue

            # Build message payload
            if current_image_path:
                try:
                    b64_str, mime = encode_image_to_base64(current_image_path)
                    data_uri = f"data:{mime};base64,{b64_str}"
                    user_content = [
                        {"type": "text", "text": user_input},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_uri
                            }
                        }
                    ]
                    # Reset image after attaching
                    current_image_path = None
                except Exception as e:
                    print(f"[!] Failed to encode image: {e}")
                    user_content = user_input
            else:
                user_content = user_input

            history.append({"role": "user", "content": user_content})

            print("\n[Local Model is thinking...]")
            reply = send_chat_message(history)
            history.append({"role": "assistant", "content": reply})

            print(f"\nAI_Local > {reply}\n")

        except KeyboardInterrupt:
            print("\n[Chat] Interrupted by user. Exiting.")
            break
        except requests.exceptions.HTTPError as e:
            print(f"\n[!] API Error: {e}")
            if e.response is not None:
                print(f"[!] Details: {e.response.text}\n")
        except Exception as e:
            print(f"\n[!] Error: {e}\n")

def main():
    parser = argparse.ArgumentParser(description="Interactive Chat & Image Interface for Local Model")
    parser.add_argument("--image", help="Optional path to image file to attach on launch")
    args = parser.parse_args()

    run_interactive_chat(args.image)

if __name__ == "__main__":
    main()
