// ==========================================================================
// Maritime AI Studio - Frontend Controller
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
  // Elements - Tabs
  const tabVerifyBtn  = document.getElementById("tabVerifyBtn");
  const tabBrowserBtn = document.getElementById("tabBrowserBtn");
  const tabChatBtn    = document.getElementById("tabChatBtn");
  const verifySection  = document.getElementById("verifySection");
  const browserSection = document.getElementById("browserSection");
  const chatSection    = document.getElementById("chatSection");

  // Elements - Live Browser
  const liveFrame         = document.getElementById("liveFrame");
  const browserIdle       = document.getElementById("browserIdle");
  const actionLabel       = document.getElementById("actionLabel");
  const statusDot         = document.getElementById("statusDot");
  const wsStatus          = document.getElementById("wsStatus");
  const browserUrlText    = document.getElementById("browserUrlText");
  const browserFrameCounter = document.getElementById("browserFrameCounter");
  const liveBadgeHeader   = document.getElementById("liveBadgeHeader");
  const replayPanel       = document.getElementById("replayPanel");
  const replayScrubber    = document.getElementById("replayScrubber");
  const replayFrameLabel  = document.getElementById("replayFrameLabel");

  let capturedFrames = [];  // ring buffer for replay
  let wsScreencast   = null;
  let wsConnected    = false;

  // --------------------------------------------------------------------------
  // Tab Switching
  // --------------------------------------------------------------------------
  function showTab(name) {
    tabVerifyBtn.classList.toggle("active",  name === "verify");
    tabBrowserBtn.classList.toggle("active", name === "browser");
    tabChatBtn.classList.toggle("active",   name === "chat");
    verifySection.classList.toggle("active",  name === "verify");
    browserSection.classList.toggle("active", name === "browser");
    chatSection.classList.toggle("active",   name === "chat");
  }

  tabVerifyBtn.addEventListener("click",  () => showTab("verify"));
  tabBrowserBtn.addEventListener("click", () => showTab("browser"));
  tabChatBtn.addEventListener("click",    () => showTab("chat"));

  // --------------------------------------------------------------------------
  // Live Browser WebSocket Screencast
  // --------------------------------------------------------------------------

  function connectScreencastWS() {
    if (wsScreencast && wsScreencast.readyState <= 1) return; // already connected/connecting

    wsStatus.textContent = "⬤ Connecting...";
    wsStatus.className = "ws-status ws-connecting";

    // Get WS URL from health endpoint or fallback to current host
    fetch("/api/health")
      .then(r => r.json())
      .then(info => {
        const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsHost = window.location.hostname || "127.0.0.1";
        const wsUrl = `${wsProtocol}//${wsHost}:8001/screencast`;
        wsScreencast = new WebSocket(wsUrl);

        wsScreencast.onopen = () => {
          wsConnected = true;
          wsStatus.textContent = "⬤ Connected";
          wsStatus.className = "ws-status ws-connected";
        };

        wsScreencast.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === "frame" || msg.type === "replay_frame") {
              onNewFrame(msg);
            } else if (msg.type === "label") {
              updateActionLabel(msg.label);
            } else if (msg.type === "status") {
              onLiveStatusChange(msg.live);
            } else if (msg.type === "meta") {
              // Received on connect — restore last known state
              if (msg.total_frames > 0) {
                replayScrubber.max = msg.total_frames - 1;
                if (!msg.live) showReplayPanel();
              }
              updateActionLabel(msg.label || "Idle");
            }
          } catch (e) { /* ignore parse errors */ }
        };

        wsScreencast.onclose = () => {
          wsConnected = false;
          wsStatus.textContent = "⬤ Disconnected";
          wsStatus.className = "ws-status ws-error";
          // Reconnect after 3s
          setTimeout(connectScreencastWS, 3000);
        };

        wsScreencast.onerror = () => {
          wsStatus.textContent = "⬤ Error";
          wsStatus.className = "ws-status ws-error";
        };
      })
      .catch(() => setTimeout(connectScreencastWS, 3000));
  }

  function onNewFrame(msg) {
    // Show frame in live view
    liveFrame.src = msg.data;
    liveFrame.style.display = "block";
    browserIdle.style.display = "none";

    // Update label and URL
    if (msg.label) updateActionLabel(msg.label);

    // Extract URL from label if it starts with 'Navigating'
    if (msg.label && msg.label.startsWith("Navigating")) {
      const match = msg.label.match(/(https?:\/\/[^\s]+)/);
      if (match) browserUrlText.textContent = match[1];
    }

    // Push to capture buffer
    capturedFrames.push({ data: msg.data, label: msg.label || "" });
    const total = capturedFrames.length;
    browserFrameCounter.textContent = `${total} frame${total !== 1 ? "s" : ""}`;

    // Update scrubber range
    replayScrubber.max = total - 1;
    replayScrubber.value = total - 1;
  }

  function updateActionLabel(label) {
    actionLabel.textContent = label || "Idle";
  }

  function onLiveStatusChange(isLive) {
    if (isLive) {
      statusDot.classList.add("live");
      liveBadgeHeader.style.display = "flex";
      replayPanel.style.display = "none";
      // Auto-switch to browser tab when live starts
      showTab("browser");
    } else {
      statusDot.classList.remove("live");
      liveBadgeHeader.style.display = "none";
      if (capturedFrames.length > 0) showReplayPanel();
    }
  }

  function showReplayPanel() {
    replayPanel.style.display = "block";
    replayScrubber.max = capturedFrames.length - 1;
    replayScrubber.value = capturedFrames.length - 1;
    updateReplayLabel(capturedFrames.length - 1);
  }

  function updateReplayLabel(idx) {
    replayFrameLabel.textContent = `Frame ${idx + 1} / ${capturedFrames.length}  •  ${capturedFrames[idx]?.label || ""}`;
  }

  function showReplayFrame(idx) {
    idx = Math.max(0, Math.min(idx, capturedFrames.length - 1));
    const frame = capturedFrames[idx];
    if (!frame) return;
    liveFrame.src = frame.data;
    liveFrame.style.display = "block";
    browserIdle.style.display = "none";
    actionLabel.textContent = frame.label;
    replayScrubber.value = idx;
    updateReplayLabel(idx);
  }

  // Replay scrubber events
  replayScrubber.addEventListener("input", () => showReplayFrame(parseInt(replayScrubber.value)));
  document.getElementById("replayFirst").addEventListener("click", () => showReplayFrame(0));
  document.getElementById("replayLast").addEventListener("click",  () => showReplayFrame(capturedFrames.length - 1));
  document.getElementById("replayPrev").addEventListener("click",  () => showReplayFrame(parseInt(replayScrubber.value) - 1));
  document.getElementById("replayNext").addEventListener("click",  () => showReplayFrame(parseInt(replayScrubber.value) + 1));

  // Connect WebSocket on page load
  connectScreencastWS();
  // Re-attempt connection when Live Browser tab is opened
  tabBrowserBtn.addEventListener("click", connectScreencastWS);

  // --------------------------------------------------------------------------
  // Verification Studio elements
  // --------------------------------------------------------------------------
  const dropzone            = document.getElementById("dropzone");
  const batchFileInput      = document.getElementById("batchFileInput");
  const btnBrowseFiles      = document.getElementById("btnBrowseFiles");
  const fileListPreview     = document.getElementById("fileListPreview");
  const btnRunVerification  = document.getElementById("btnRunVerification");
  const resultsContainer    = document.getElementById("resultsContainer");
  const resultStatusBadge   = document.getElementById("resultStatusBadge");
  const docMatrixBody       = document.getElementById("docMatrixBody");
  const profileDetails      = document.getElementById("profileDetails");
  const resultScreenshotImg = document.getElementById("resultScreenshotImg");

  // Chat elements
  const chatMessages      = document.getElementById("chatMessages");
  const chatForm          = document.getElementById("chatForm");
  const userPromptInput   = document.getElementById("userPromptInput");
  const chatFileInput     = document.getElementById("chatFileInput");
  const btnAttach         = document.getElementById("btnAttach");
  const attachmentPreview = document.getElementById("attachmentPreview");
  const previewImg        = document.getElementById("previewImg");
  const previewFilename   = document.getElementById("previewFilename");
  const btnRemoveAttachment = document.getElementById("btnRemoveAttachment");
  const modelSelect       = document.getElementById("modelSelect");

  let selectedBatchFiles = [];
  let chatAttachmentUri  = null;
  let chatHistory        = [];

  // --------------------------------------------------------------------------
  // Verification Studio - File Handling & Dropzone
  // --------------------------------------------------------------------------
  btnBrowseFiles.addEventListener("click", () => batchFileInput.click());
  dropzone.addEventListener("click", (e) => {
    if (e.target !== btnBrowseFiles) batchFileInput.click();
  });

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
      handleBatchFiles(e.dataTransfer.files);
    }
  });

  batchFileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleBatchFiles(e.target.files);
    }
  });

  function handleBatchFiles(files) {
    selectedBatchFiles = Array.from(files);
    renderFileList();
    btnRunVerification.disabled = selectedBatchFiles.length === 0;
  }

  function renderFileList() {
    fileListPreview.innerHTML = "";
    selectedBatchFiles.forEach((file) => {
      const chip = document.createElement("div");
      chip.className = "file-chip";
      chip.innerHTML = `<span>📄</span> <span>${file.name}</span> <small>(${(file.size / 1024).toFixed(1)} KB)</small>`;
      fileListPreview.appendChild(chip);
    });
  }

  // --------------------------------------------------------------------------
  // Verification Studio - Execute LangGraph Pipeline
  // --------------------------------------------------------------------------
  btnRunVerification.addEventListener("click", async () => {
    if (selectedBatchFiles.length === 0) return;

    btnRunVerification.disabled = true;
    btnRunVerification.innerHTML = `<span class="pulse-dot"></span> Orchestrating LangGraph...`;
    resultsContainer.style.display = "none";

    // Reset Stepper
    setStep(1);

    const formData = new FormData();
    selectedBatchFiles.forEach((file) => {
      formData.append("files", file);
    });

    try {
      // Step 1: Ingesting
      setStep(1);

      // Simulate stepper progression for UX while waiting for backend
      setTimeout(() => setStep(2), 1500);
      setTimeout(() => setStep(3), 3500);
      setTimeout(() => setStep(4), 5500);

      const resp = await fetch("/api/verify-batch", {
        method: "POST",
        body: formData
      });

      if (!resp.ok) {
        throw new Error(`Server returned ${resp.status}`);
      }

      const data = await resp.json();
      setStep(5);
      renderVerificationResults(data);

    } catch (err) {
      alert(`Verification execution error: ${err.message}`);
    } finally {
      btnRunVerification.disabled = false;
      btnRunVerification.innerHTML = `Execute LangGraph Verification`;
    }
  });

  function setStep(stepNumber) {
    for (let i = 1; i <= 5; i++) {
      const stepElem = document.getElementById(`step${i}`);
      if (!stepElem) continue;
      if (i < stepNumber) {
        stepElem.className = "step-item completed";
      } else if (i === stepNumber) {
        stepElem.className = "step-item active";
      } else {
        stepElem.className = "step-item";
      }
    }
  }

  function renderVerificationResults(data) {
    resultsContainer.style.display = "flex";

    // Status Badge
    const status = data.status || "COMPLETED";
    resultStatusBadge.textContent = status;
    resultStatusBadge.className = `status-badge ${status.toLowerCase()}`;

    // 1. Render Document Matrix
    docMatrixBody.innerHTML = "";
    const matrix = data.document_matrix || [];
    if (matrix.length === 0) {
      docMatrixBody.innerHTML = `<tr><td colspan="4" style="text-align:center;">No document breakdown returned</td></tr>`;
    } else {
      matrix.forEach((doc) => {
        const isSuccess = doc.status === "SUCCESS";
        const badgeClass = isSuccess ? "badge-tag success" : "badge-tag failed";
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${doc.file_name}</strong></td>
          <td><span class="country-pill">${doc.doc_type || "N/A"}</span></td>
          <td><span class="${badgeClass}">${doc.status}</span></td>
          <td>${doc.error ? `<span style="color:var(--accent-rose);">${doc.error}</span>` : "Extracted successfully"}</td>
        `;
        docMatrixBody.appendChild(tr);
      });
    }

    // 2. Render Profile Details
    profileDetails.innerHTML = "";
    const prof = data.profile || {};
    const details = [
      { label: "Seafarer Name", value: prof.full_name || "N/A" },
      { label: "Nationality", value: prof.nationality || data.country_resolved || "N/A" },
      { label: "Date of Birth", value: prof.dob || "N/A" },
      { label: "CoC / Blanko No.", value: prof.coc_number || "N/A" },
      { label: "CDC / Seaman No.", value: prof.cdc_number || "N/A" },
      { label: "Resolved Portal", value: data.country_resolved || "N/A" }
    ];

    details.forEach((d) => {
      const row = document.createElement("div");
      row.className = "profile-row";
      row.innerHTML = `<span class="profile-label">${d.label}</span><span class="profile-value">${d.value}</span>`;
      profileDetails.appendChild(row);
    });

    // 3. Render Screenshot
    if (data.screenshot_data_uri) {
      resultScreenshotImg.src = data.screenshot_data_uri;
      resultScreenshotImg.style.display = "block";
    } else {
      resultScreenshotImg.style.display = "none";
    }

    // Scroll to results
    resultsContainer.scrollIntoView({ behavior: "smooth" });
  }

  // --------------------------------------------------------------------------
  // Chat Studio Controller
  // --------------------------------------------------------------------------
  btnAttach.addEventListener("click", () => chatFileInput.click());

  chatFileInput.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const resp = await fetch("/api/upload", {
        method: "POST",
        body: formData
      });
      const res = await resp.json();
      chatAttachmentUri = res.data_uri;
      previewImg.src = res.data_uri;
      previewFilename.textContent = file.name;
      attachmentPreview.style.display = "flex";
    } catch (err) {
      alert("Failed to upload image preview");
    }
  });

  btnRemoveAttachment.addEventListener("click", () => {
    chatAttachmentUri = null;
    chatFileInput.value = "";
    attachmentPreview.style.display = "none";
  });

  chatForm.addEventListener("submit", async () => {
    const text = userPromptInput.value.trim();
    if (!text && !chatAttachmentUri) return;

    appendMessage("user", text, chatAttachmentUri);
    userPromptInput.value = "";

    const currentImg = chatAttachmentUri;
    chatAttachmentUri = null;
    attachmentPreview.style.display = "none";

    const provider = modelSelect.value;
    const msgPayload = { role: "user" };

    if (currentImg) {
      msgPayload.content = [
        { type: "text", text: text },
        { type: "image_url", image_url: { url: currentImg } }
      ];
    } else {
      msgPayload.content = text;
    }

    chatHistory.push(msgPayload);

    try {
      const resp = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonPayload({
          model_provider: provider,
          messages: chatHistory
        })
      });

      const data = await resp.json();
      const reply = data.response || data.detail || "No response received.";
      appendMessage("assistant", reply);
      chatHistory.push({ role: "assistant", content: reply });
    } catch (err) {
      appendMessage("assistant", `Error: ${err.message}`);
    }
  });

  function jsonPayload(obj) {
    return JSON.stringify(obj);
  }

  function appendMessage(role, text, imageUri = null) {
    const art = document.createElement("article");
    art.className = `message ${role}`;
    
    let imgHtml = "";
    if (imageUri) {
      imgHtml = `<img src="${imageUri}" class="message-image" alt="User attachment">`;
    }

    art.innerHTML = `
      <div class="avatar">${role === "user" ? "YOU" : "AI"}</div>
      <div class="bubble">
        <p>${text.replace(/\n/g, "<br>")}</p>
        ${imgHtml}
      </div>
    `;
    chatMessages.appendChild(art);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
});
