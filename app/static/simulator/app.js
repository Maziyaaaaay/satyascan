(function () {
  const chatLog = document.getElementById("chat-log");
  const composer = document.getElementById("composer");
  const textInput = document.getElementById("text-input");
  const imageInput = document.getElementById("image-input");
  const imagePreviewRow = document.getElementById("image-preview-row");
  const imagePreview = document.getElementById("image-preview");
  const imageClear = document.getElementById("image-clear");
  const languageSelect = document.getElementById("language-select");

  let sessionId = localStorage.getItem("satyascan_sim_session_id");
  if (!sessionId) {
    sessionId = "sess-" + Math.random().toString(36).slice(2, 12);
    localStorage.setItem("satyascan_sim_session_id", sessionId);
  }

  let pendingImageBase64 = null;

  function addBubble(text, direction, opts) {
    opts = opts || {};
    const bubble = document.createElement("div");
    bubble.className = "bubble bubble-" + direction + (opts.pending ? " bubble-pending" : "");

    if (opts.imageDataUrl) {
      const img = document.createElement("img");
      img.className = "attached";
      img.src = opts.imageDataUrl;
      bubble.appendChild(img);
    }

    const textNode = document.createElement("div");
    textNode.textContent = text;
    bubble.appendChild(textNode);

    if (opts.meta) {
      const meta = document.createElement("div");
      meta.className = "bubble-meta";
      meta.textContent = opts.meta;
      bubble.appendChild(meta);
    }

    if (opts.sources && opts.sources.length) {
      const list = document.createElement("ul");
      list.className = "sources-list";
      opts.sources.forEach((url) => {
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.href = url;
        a.textContent = url;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        li.appendChild(a);
        list.appendChild(li);
      });
      bubble.appendChild(list);
    }

    chatLog.appendChild(bubble);
    chatLog.scrollTop = chatLog.scrollHeight;
    return bubble;
  }

  imageInput.addEventListener("change", () => {
    const file = imageInput.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      pendingImageBase64 = reader.result.split(",")[1];
      imagePreview.src = reader.result;
      imagePreviewRow.hidden = false;
    };
    reader.readAsDataURL(file);
  });

  imageClear.addEventListener("click", () => {
    pendingImageBase64 = null;
    imageInput.value = "";
    imagePreviewRow.hidden = true;
  });

  composer.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = textInput.value.trim();
    const imageBase64 = pendingImageBase64;
    const imageDataUrl = imageBase64 ? imagePreview.src : null;

    if (!text && !imageBase64) return;

    addBubble(text || "(image)", "out", { imageDataUrl });
    textInput.value = "";
    pendingImageBase64 = null;
    imageInput.value = "";
    imagePreviewRow.hidden = true;

    const pendingBubble = addBubble("Checking…", "in", { pending: true });

    try {
      const response = await fetch("/simulator/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          text: text || null,
          image_base64: imageBase64,
          language: languageSelect.value,
        }),
      });
      const data = await response.json();
      pendingBubble.remove();

      const meta = data.verdict
        ? `Verdict: ${data.verdict} · Confidence: ${data.confidence_label} (${Math.round((data.confidence_score || 0) * 100)}%)`
        : null;

      addBubble(data.explanation || "Sorry, something went wrong.", "in", {
        meta,
        sources: data.sources,
      });
    } catch (err) {
      pendingBubble.remove();
      addBubble("Network error - is the SatyaScan backend running?", "in");
    }
  });
})();
