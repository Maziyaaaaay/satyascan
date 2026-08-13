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

  const VERDICT_META = {
    true: { label: "TRUE", emoji: "✅", className: "verdict-true" },
    false: { label: "FALSE", emoji: "❌", className: "verdict-false" },
    misleading: { label: "MISLEADING", emoji: "⚠️", className: "verdict-misleading" },
    unverifiable: { label: "UNVERIFIABLE", emoji: "❓", className: "verdict-unverifiable" },
    satire: { label: "SATIRE", emoji: "🎭", className: "verdict-satire" },
  };

  const CONFIDENCE_CLASS = { high: "confidence-high", medium: "confidence-medium", low: "confidence-low" };

  function addPlainBubble(text, direction, opts) {
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

    chatLog.appendChild(bubble);
    chatLog.scrollTop = chatLog.scrollHeight;
    return bubble;
  }

  function addResultBubble(data) {
    const bubble = document.createElement("div");
    bubble.className = "bubble bubble-in bubble-result";

    if (data.verdict && VERDICT_META[data.verdict]) {
      const meta = VERDICT_META[data.verdict];
      const badge = document.createElement("div");
      badge.className = "verdict-badge " + meta.className;
      badge.textContent = meta.emoji + " " + meta.label;
      bubble.appendChild(badge);
    }

    if (typeof data.confidence_score === "number") {
      const pct = Math.round(data.confidence_score * 100);
      const confClass = CONFIDENCE_CLASS[data.confidence_label] || "confidence-low";

      const wrap = document.createElement("div");
      wrap.className = "confidence-wrap";

      const label = document.createElement("div");
      label.className = "confidence-label";
      label.textContent = "Confidence: " + pct + "% (" + (data.confidence_label || "unknown") + ")";
      wrap.appendChild(label);

      const track = document.createElement("div");
      track.className = "confidence-track";
      const fill = document.createElement("div");
      fill.className = "confidence-fill " + confClass;
      fill.style.width = pct + "%";
      track.appendChild(fill);
      wrap.appendChild(track);

      bubble.appendChild(wrap);
    }

    const explanation = document.createElement("div");
    explanation.className = "result-explanation";
    explanation.textContent = data.explanation || "Sorry, something went wrong.";
    bubble.appendChild(explanation);

    if (data.rationale) {
      const why = document.createElement("div");
      why.className = "result-rationale";
      why.innerHTML = "<strong>Why:</strong> ";
      why.appendChild(document.createTextNode(data.rationale));
      bubble.appendChild(why);
    }

    if (data.image_match_count !== null && data.image_match_count !== undefined) {
      const imgSummary = document.createElement("div");
      imgSummary.className = "result-image-summary";
      imgSummary.textContent =
        data.image_match_count > 0
          ? `🖼️ This image was found on ${data.image_match_count} other page(s) online.`
          : "🖼️ No matching source was found for this image online.";
      bubble.appendChild(imgSummary);

      if (data.image_ocr_text) {
        const ocr = document.createElement("div");
        ocr.className = "result-image-summary";
        ocr.textContent = "Text detected in image: “" + data.image_ocr_text + "”";
        bubble.appendChild(ocr);
      }
    }

    if (data.sources && data.sources.length) {
      const sourcesHeading = document.createElement("div");
      sourcesHeading.className = "sources-heading";
      sourcesHeading.textContent = "Checked against these sources:";
      bubble.appendChild(sourcesHeading);

      const list = document.createElement("ul");
      list.className = "sources-list";
      data.sources.forEach((source) => {
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.href = source.url;
        a.textContent = source.domain || source.url;
        a.title = source.url;
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

    addPlainBubble(text || "(image)", "out", { imageDataUrl });
    textInput.value = "";
    pendingImageBase64 = null;
    imageInput.value = "";
    imagePreviewRow.hidden = true;

    const pendingBubble = addPlainBubble("Checking…", "in", { pending: true });

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
      addResultBubble(data);
    } catch (err) {
      pendingBubble.remove();
      addPlainBubble("Network error - is the SatyaScan backend running?", "in");
    }
  });
})();
