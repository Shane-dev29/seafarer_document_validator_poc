# Project Memory & Context Handoff

> **Purpose:** This file maintains project state, history, architecture, and current status so that any future AI model, agent, or developer can immediately pick up where work was left off without loss of context.
>
> **LIVING DOCUMENT DIRECTIVE:** Any agent or model interacting with this repository MUST actively update this file whenever new files are created, architectural decisions are made, tasks are completed, or user preferences change.

---

## 1. Project Overview & Objective
- **Workspace:** `c:\Users\remed\Desktop\anti_dummy`
- **Core Focus:** 
  1. Autonomous maritime seafarer credential verification pipeline.
  2. Ingests COC, CDC, FOC, Passport, and other seafarer documents.
  3. Uses **Local LLM (`AI_Local`)** for private PII data extraction (preserving full data confidentiality).
  4. Uses **Frontier Model (`gemini-3.6-flash`)** for DOM inspection, scraper generation, unlisted country research, and visual CAPTCHA decoding.
  5. Orchestrates workflows via **LangGraph**, **MCP Verifier Registry**, and **Playwright** browser automation.
- **Key Requirement:** Zero manual script execution required (background directory dropzone watcher polls `incoming_docs/` and produces verified audit reports in `verified_reports/`).

---

## 2. Environment & Dependencies
- **OS:** Windows (PowerShell shell)
- **Python Version:** `Python 3.10.11`
- **Installed Packages:**
  - `playwright` (v1.62.0) with Chromium browser binary installed
  - `pyee` (v13.0.1)
  - `beautifulsoup4` (v4.12.3)
  - `google-genai` (v0.1.1)
  - `fastmcp` (v0.1.0)
  - `requests`, `pandas`, `openpyxl`, `pydantic`
- **Endpoints & Configurations (`.env`):**
  - Local LLM: `https://ai.edot-solutions.com/v1/chat/completions` (Model: `AI_Local`)
  - Local OCR: `http://192.168.1.34:8007/api/extract?mode=structured`
  - Frontier Model: Google Gemini API (`gemini-3.6-flash`)
  - Web Server: `http://127.0.0.1:8000`

---

## 3. Workspace Files & Artifacts

| File / Directory | Purpose | Status |
| :--- | :--- | :--- |
| [`README.md`](file:///c:/Users/remed/Desktop/anti_dummy/README.md) | Comprehensive system documentation, quick start guide, architecture diagram, and command reference. | **Active & Current** |
| [`memory.md`](file:///c:/Users/remed/Desktop/anti_dummy/memory.md) | Project state, history, living memory, and developer handoff context. | **Active** |
| [`main.py`](file:///c:/Users/remed/Desktop/anti_dummy/main.py) | Master CLI entrypoint for the end-to-end LangGraph verification orchestrator (`--pdf` or manual flags). | **Active & Operational** |
| [`IMO_STCW_Seafarer_Verification.xlsx`](file:///c:/Users/remed/Desktop/anti_dummy/IMO_STCW_Seafarer_Verification.xlsx) | Master IMO maritime authority database mapping countries to official verification portals. | **Active Database** |
| [`verify_indonesia_live.py`](file:///c:/Users/remed/Desktop/anti_dummy/verify_indonesia_live.py) | Live runner for Indonesia Dephub portal. Integrates Local LLM extraction, PDF attachment, Frontier CAPTCHA solving, and form submission. | **Active & Verified** |
| [`verify_myanmar_aio.py`](file:///c:/Users/remed/Desktop/anti_dummy/verify_myanmar_aio.py) | Direct verification script for Myanmar DMAOS All-In-One Self-Verification portal (`dmamyanmar.org`). | **Active & Verified (Status: VALID)** |
| [`run_visible_verification.py`](file:///c:/Users/remed/Desktop/anti_dummy/run_visible_verification.py) | Multi-country visual test runner for visible browser automation testing. | **Active** |
| [`indos_checker.py`](file:///c:/Users/remed/Desktop/anti_dummy/indos_checker.py) | Standalone interactive Playwright script for Indian INDoS & CoC verification. | **Active & Ready** |
| [`research_country.py`](file:///c:/Users/remed/Desktop/anti_dummy/research_country.py) | Autonomous research agent querying Gemini for unlisted maritime procedures and creating verification guides. | **Active** |
| [`chat_local_model.py`](file:///c:/Users/remed/Desktop/anti_dummy/chat_local_model.py) | Terminal chat interface with image attachment (`/image`) support for `AI_Local`. | **Active** |
| [`capture_page.py`](file:///c:/Users/remed/Desktop/anti_dummy/capture_page.py) | Utility to render websites, capture screenshots, and parse DOM with BeautifulSoup. | **Active** |
| [`discover_fields.py`](file:///c:/Users/remed/Desktop/anti_dummy/discover_fields.py) | Headless inspection script that runs Playwright against any URL to discover all input fields and labels. | **Active** |
| [`scrape_results.py`](file:///c:/Users/remed/Desktop/anti_dummy/scrape_results.py) | Generic interactive scraper prompting user for form inputs. | **Active** |
| [`sample_certificate.pdf`](file:///c:/Users/remed/Desktop/anti_dummy/sample_certificate.pdf) | Minimal valid 1-page PDF used for verification file upload fields (e.g. Indonesian Validasi TTE). | **Active Asset** |
| [`core/`](file:///c:/Users/remed/Desktop/anti_dummy/core) | Configuration (`config.py`), Pydantic models (`schemas.py`), and OCR client with exponential backoff (`ocr_client.py`). | **Core Module** |
| [`local_llm/`](file:///c:/Users/remed/Desktop/anti_dummy/local_llm) | Private data extraction (`extractor.py`) and multi-doc classifier (`multi_doc_classifier.py`). | **Core Module** |
| [`frontier_llm/`](file:///c:/Users/remed/Desktop/anti_dummy/frontier_llm) | Frontier Gemini client (`gemini_client.py`) for code generation, unlisted research, and CAPTCHA vision solving. | **Core Module** |
| [`registry/`](file:///c:/Users/remed/Desktop/anti_dummy/registry) | Country resolution and portal lookup with expanded ISO-3 and demonym aliases (`excel_registry.py`). | **Core Module** |
| [`mcp_server/`](file:///c:/Users/remed/Desktop/anti_dummy/mcp_server) | FastMCP server (`server.py`) and registry service (`registry_service.py`) managing country verifiers. | **Core Module** |
| [`orchestrator/`](file:///c:/Users/remed/Desktop/anti_dummy/orchestrator) | LangGraph StateGraph (`workflow.py`), dynamic scraper synthesis (`auto_scraper_agent.py`), and unlisted country researcher (`unlisted_country_researcher.py`). | **Core Module** |
| [`verifiers/`](file:///c:/Users/remed/Desktop/anti_dummy/verifiers) | Modular Playwright verifiers container (`base_verifier.py`). Currently 100% clean with zero pre-cached country verifiers for fresh end-to-end testing. | **Clean Container** |
| [`service/watcher.py`](file:///c:/Users/remed/Desktop/anti_dummy/service/watcher.py) | Background dropzone folder watcher polling `incoming_docs/` and generating reports. | **Active Daemon** |
| [`web_app/`](file:///c:/Users/remed/Desktop/anti_dummy/web_app) | Threaded backend HTTP server (`server.py`) + oceanic glassmorphism frontend (`static/`). | **Active Daemon (Port 8000)** |
| [`screenshots/`](file:///c:/Users/remed/Desktop/anti_dummy/screenshots) | Archive of verified live portal screenshots across India, Myanmar, and Indonesia. | **Storage** |
| [`incoming_docs/`](file:///c:/Users/remed/Desktop/anti_dummy/incoming_docs) | Ingestion dropzone for seafarer batch folders. | **Dropzone** |
| [`processed_docs/`](file:///c:/Users/remed/Desktop/anti_dummy/processed_docs) | Archive of ingested seafarer documents. | **Storage** |
| [`verified_reports/`](file:///c:/Users/remed/Desktop/anti_dummy/verified_reports) | Output verification JSON reports and full-page audit screenshots. | **Storage** |

---

## 4. History of Completed Phases

### Phase 1 to 6: Core Setup & Initial Testing
- Installed Playwright Chromium browser binary.
- Built interactive INDoS verifier (`indos_checker.py`) tested live against DG Shipping portal.
- Integrated local LiteLLM `AI_Local` and Swagger OCR client (`192.168.1.34:8007`).

### Phase 7: Complete End-to-End LangGraph Pipeline
- Tied OCR $\rightarrow$ Local LLM entity extraction $\rightarrow$ Excel registry lookup $\rightarrow$ MCP registry $\rightarrow$ Playwright verification.
- Verified live end-to-end with Indian Chief Mate profile (`ANUP KAMBOJ`, `09NL5250`) returning `VERIFIED` with 4 records.

### Phase 8 to 12: Multi-Country Expansion & Unlisted Country Research
- Expanded Excel registry with ISO 3166-1 alpha-3 codes and demonym aliases.
- Built Autonomous Unlisted Country Researcher (`research_country.py`) synthesizing official procedures.
- Investigated Myanmar DMA portal and updated to the active **DMAOS All-In-One Self-Verification portal** (`https://www.dmamyanmar.org/AllInOneCertificate/SelfVerification`), successfully verifying seafarer `HEIN HTET` (`MK670211`, `2DK004368`, `80484`) with **Status: VALID**.

### Phase 13: Local Maritime AI Studio (Web UI)
- Built full-stack glassmorphism web app (`web_app/server.py` on `http://127.0.0.1:8000`) featuring real-time AI model switching, drag-and-drop file uploaders, and interactive chat.

### Phase 14: Indonesian Maritime Portal (Dephub) Verification with CAPTCHA & File Upload
- **Target Portal:** `https://pelaut.dephub.go.id/index.php/verifikasi` (Direktorat Jenderal Perhubungan Laut)
- **Features Implemented in [`verifiers/indonesia_verifier.py`](file:///c:/Users/remed/Desktop/anti_dummy/verifiers/indonesia_verifier.py) & [`verify_indonesia_live.py`](file:///c:/Users/remed/Desktop/anti_dummy/verify_indonesia_live.py):**
  1. Extracted seafarer profile (`SEAFARE_CODE`, `BLANKO_DISPLAY_CODE`, name, DOB) via Local Model (`AI_Local`).
  2. Attached certificate document to `#DOKUMEN_SERTIFIKAT` (`sample_certificate.pdf` or seafarer PDF).
  3. Captured live CAPTCHA element (`.captcha img`), decoded jumbled alphanumeric characters via Frontier Gemini Vision (`solve_captcha`), and filled decoded code into `#captcha`.
  4. Submitted verification form via `button[type="submit"]` (`Cek | Check`) and saved verification screenshots (`indonesia_form_filled.png`, `indonesia_verification_result.png`).

### Phase 15: Workspace Cleanup & Comprehensive User Guide
- Removed unnecessary scratch HTML dumps (`coc_search_dump.html`, `indonesia_page_dump.html`), duplicate test scripts (`test_captcha_and_upload.py`, `scrape_and_verify_indonesia.py`), and redundant scratch image files.
- Archived key verification screenshots into [`screenshots/`](file:///c:/Users/remed/Desktop/anti_dummy/screenshots).
- Created comprehensive documentation in [`README.md`](file:///c:/Users/remed/Desktop/anti_dummy/README.md).

### Phase 16: Unified LangGraph State Machine & Web Studio Dashboard
- **Fast-Fail OCR Policy ([`core/ocr_client.py`](file:///c:/Users/remed/Desktop/anti_dummy/core/ocr_client.py)):** Replaced 3-attempt exponential retry delays with a 10s single-pass request. Files that fail OCR are immediately marked as `OCR_FAILED` in the audit matrix without stalling the pipeline.
- **Unified LangGraph Pipeline ([`orchestrator/workflow.py`](file:///c:/Users/remed/Desktop/anti_dummy/orchestrator/workflow.py)):** Unified folder ingestion, multi-doc entity synthesis, national portal lookup, browser automation, and audit report generation into a single LangGraph StateGraph.
- **Full-Stack Verification Studio ([`web_app/`](file:///c:/Users/remed/Desktop/anti_dummy/web_app)):** Deployed dual-tab UI at `http://127.0.0.1:8000` with drag-and-drop batch upload, live 5-step stepper, document pass/fail status table, and screenshot viewer.

---

## 5. Critical User Preferences & Guidelines
- **Zero Manual Script Running:** The user drops files into `incoming_docs/` and receives final verification reports asynchronously in `verified_reports/`.
- **Two-Tier Intelligence:** Private seafarer data stays on local models; heavy-lifting web scraping and script generation uses the Gemini Frontier Model (`gemini-3.6-flash`).
- **Multi-Doc Focus:** Emphasize extraction across COC, CDC, and FOC.
- **Self-Healing MCP Registry:** Missing country verifiers are autonomously written by Gemini, registered to MCP, and cached permanently.
- **Strict Browser-Side Automation:** All verifications run via physical/headless browser UI automation.
- **Living Document Rule:** Maintain continuous updates to this file as progress is made.

---

## 6. Current Roadmap / Recommended Next Steps
1. **Flag State (FOC) Secondary Fallback:** Check secondary Flag State endorsements (Liberia, Panama, Marshall Islands) if a seafarer's national authority requires manual email processing.
2. **Docling Integration:** Supplement local OCR server (`192.168.1.34:8007`) with `docling` for offline, multi-page PDF & table parsing.
3. **Continue Expanding Batch Ingestion:** Process additional foreign seafarer batches through the dropzone watcher.
