# Autonomous Maritime Seafarer Credential Verification System

An autonomous, modular maritime document verification pipeline combining **Local LLMs**, **Frontier AI Models (Google Gemini)**, **MCP Verifier Registries**, and **Playwright Browser Automation** to ingest seafarer credentials (COC, CDC, FOC, Passport), discover official maritime administration portals, and execute verification in real time.

---

## 📑 Architecture Overview

```
                      ┌──────────────────────────────────────────────┐
                      │ 1. INGESTION (PDF / JPG / Multiple Scans)    │
                      │    - Drop into 'incoming_docs/'              │
                      │    - Or upload via Web UI (127.0.0.1:8000)   │
                      └───────────────────────┬──────────────────────┘
                                              ▼
                      ┌──────────────────────────────────────────────┐
                      │ 2. PRIVATE DATA EXTRACTION (Local AI_Local)  │
                      │    - Extracts Seafarer Name, DOB, CDC, COC   │
                      │    - Strict privacy (No PII sent to cloud)   │
                      └───────────────────────┬──────────────────────┘
                                              ▼
                      ┌──────────────────────────────────────────────┐
                      │ 3. MARITIME REGISTRY LOOKUP                  │
                      │    - IMO_STCW_Seafarer_Verification.xlsx     │
                      │    - Auto-resolves country & portal URL      │
                      └───────┬───────────────────────────────┬──────┘
                              │                               │
                [Cached Verifier Found]              [Unlisted Country]
                              │                               │
                              ▼                               ▼
                      ┌────────────────┐             ┌─────────────────────┐
                      │ 4A. MCP SERVER │             │ 4B. GEMINI FRONTIER │
                      │ Cached Script  │             │ Autonomous Research │
                      │ Execution      │             │ & Script Synthesis  │
                      └───────┬────────┘             └────────┬────────────┘
                              │                               │
                              └───────────────┬───────────────┘
                                              ▼
                      ┌──────────────────────────────────────────────┐
                      │ 5. PLAYWRIGHT BROWSER AUTOMATION             │
                      │    - Real Chromium browser interaction       │
                      │    - Multimodal Vision CAPTCHA solving       │
                      │    - Certificate PDF file upload             │
                      └───────────────────────┬──────────────────────┘
                                              ▼
                      ┌──────────────────────────────────────────────┐
                      │ 6. REPORT GENERATION & AUDIT LOGS            │
                      │    - verified_reports/<SEAFARER_TIMESTAMP>/  │
                      │    - JSON report + Full-page screenshot      │
                      └──────────────────────────────────────────────┘
```

---

## 🚀 Quick Start & Usage

### 1. Web Application Interface (Maritime AI Studio)

Launch the full-stack web UI with real-time model switching, drag-and-drop document upload, and interactive chat:

```powershell
python web_app/server.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

---

### 2. Autonomous Directory Watcher (Zero Manual Input)

The background service continuously monitors `incoming_docs/` for new seafarer document folders:

```powershell
python -u -m service.watcher
```
1. Create a subfolder in `incoming_docs/` (e.g. `incoming_docs/Captain_Smith/`).
2. Drop in any number of PDF or JPG scans (COC, CDC, Passport, FOC).
3. The watcher automatically classifies documents, executes verification, moves originals to `processed_docs/`, and generates reports in `verified_reports/`.

---

### 3. Country-Specific Live Verification Runners

You can test individual country portals directly with visible browser automation:

#### 🇮🇳 India (DG Shipping - INDoS & CoC Checker)
```powershell
python run_visible_verification.py --country India
# Or interactive INDoS checker:
python indos_checker.py
```
- **Portal:** `http://220.156.189.33/esamudraUI/jsp/examination/checker/COCSearch.jsp`
- **Inputs:** INDoS Number + Date of Birth

#### 🇲🇲 Myanmar (DMAOS All-In-One Self-Verification)
```powershell
python verify_myanmar_aio.py
```
- **Portal:** `https://www.dmamyanmar.org/AllInOneCertificate/SelfVerification`
- **Inputs:** CDC No., CoC Serial No., Passport No., Requester Email

#### 🇮🇩 Indonesia (Direktorat Jenderal Perhubungan Laut)
```powershell
# Visible browser on your screen:
python verify_indonesia_live.py --visible

# Headless background mode:
python verify_indonesia_live.py --headless
```
- **Portal:** `https://pelaut.dephub.go.id/index.php/verifikasi`
- **Features:** 
  - Local Model (`AI_Local`) extracts Seafarer Code & Blanko Serial No.
  - Attaches certificate PDF to `DOKUMEN_SERTIFIKAT`
  - Captures live CAPTCHA and decodes with Frontier Gemini Vision
  - Automatically fills `#captcha` and submits `Cek`

---

### 4. End-to-End CLI Orchestrator

Run the full LangGraph pipeline on a specific PDF or custom seafarer parameters:

```powershell
# Ingest PDF:
python main.py --pdf "path/to/document.pdf"

# Or manual profile:
python main.py --name "ANUP KAMBOJ" --nationality "India" --coc "09NL5250" --dob "07/09/1992"
```

---

### 5. Autonomous Unlisted Country Researcher

To research an unlisted maritime administration, discover its verification portal, and generate a new verification guide:

```powershell
python research_country.py --country "Bahamas"
```
The report is saved to `verified_reports/research_reports/Bahamas_Verification_Guide.md`.

---

### 6. Local Model Interactive Chat & Vision CLI

Interact directly with the local LiteLLM model with text and image attachment support:

```powershell
python chat_local_model.py
```
- Type `/image path/to/image.png` to attach an image for analysis.
- Type `exit` to quit.

---

## 📁 Repository Directory Structure

```
├── .env                                # API keys and local endpoint configs
├── README.md                           # This user guide
├── memory.md                           # Project state, history & handoff context
├── main.py                             # Master CLI pipeline orchestrator
├── IMO_STCW_Seafarer_Verification.xlsx # Master IMO maritime authority database
│
├── core/                               # Core schemas and configuration
│   ├── config.py                       # Environment variables and URLs
│   ├── schemas.py                      # Pydantic data contracts (SeafarerProfile, VerificationResult)
│   └── ocr_client.py                   # Document OCR client with retry logic
│
├── local_llm/                          # Private Local Model Layer (AI_Local)
│   ├── extractor.py                    # Seafarer entity extraction from text
│   └── multi_doc_classifier.py         # Multi-document classifier (COC, CDC, FOC)
│
├── frontier_llm/                       # Frontier Model Layer (Google Gemini)
│   └── gemini_client.py                # Verifier script synthesis & CAPTCHA vision solving
│
├── registry/                           # Maritime Authority Registry
│   └── excel_registry.py               # Excel country & portal lookup with ISO aliases
│
├── mcp_server/                         # MCP Verifier Tool Registry
│   ├── server.py                       # FastMCP server definition
│   └── registry_service.py             # Script discovery and registration service
│
├── orchestrator/                       # LangGraph Orchestration State Machine
│   ├── workflow.py                     # Compiled LangGraph state machine
│   ├── auto_scraper_agent.py           # Playwright scraper generation agent
│   └── unlisted_country_researcher.py  # Unlisted country web researcher
│
├── verifiers/                          # Country-Specific Playwright Verifiers
│   ├── base_verifier.py                # Abstract BaseVerifier class
│   ├── india_verifier.py               # Indian DG Shipping verifier
│   ├── myanmar_verifier.py             # Myanmar DMAOS verifier
│   └── indonesia_verifier.py           # Indonesian Dephub verifier (with CAPTCHA + Upload)
│
├── service/                            # Background Services
│   └── watcher.py                      # Automated dropzone directory watcher
│
├── web_app/                            # Full-Stack Web Application
│   ├── server.py                       # Threaded backend server & API proxy
│   └── static/                         # Glassmorphism HTML/CSS/JS interface
│
├── incoming_docs/                      # Dropzone for incoming seafarer document folders
├── processed_docs/                     # Archive of successfully processed documents
├── verified_reports/                   # Output verification reports (JSON & screenshots)
└── screenshots/                        # Reference verification screenshots
```

---

## ⚙️ Configuration (`.env`)

```env
# Local Model Endpoint (LiteLLM OpenAI-Compatible)
LLM_URL=https://ai.edot-solutions.com/v1/chat/completions
LLM_MODEL=AI_Local
LLM_API_KEY=your_local_key_here

# Local Document OCR Endpoint
OCR_URL=http://192.168.1.34:8007/api/extract?mode=structured

# Google Gemini Frontier Model API Key
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## 🔒 Privacy & Architecture Principles
- **Strict Data Privacy:** All private seafarer identification (names, DOB, document numbers) is processed exclusively by the in-house **Local Model (`AI_Local`)**.
- **Frontier Intelligence Isolation:** Cloud Frontier models (Google Gemini `gemini-3.6-flash`) are utilized strictly for non-sensitive technical operations (analyzing public DOM trees, generating Playwright verifier code, and solving visual challenge puzzles).
- **Physical Browser UI Automation:** Verifications are conducted exclusively via real browser rendering (Playwright Chromium) matching official maritime authority requirements.
