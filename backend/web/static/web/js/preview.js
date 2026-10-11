/*
 * New complaint page:
 * 1. Live AI preview: while the student types, ask the server what the AI thinks
 *    (department, confidence, urgency, language, location, spam warning).
 * 2. Voice input: speak the complaint (English, Tamil or Malayalam) using the
 *    browser's speech recognition. Only shown if the browser supports it.
 */

const T = JSON.parse(document.getElementById("i18n-messages")?.textContent || "{}");
const form = document.querySelector("form[data-preview-url]");

// ---------------- 1. Live AI preview ----------------
if (form) {
  const panel = {
    empty: document.querySelector("[data-preview-empty]"),
    loading: document.querySelector("[data-preview-loading]"),
    result: document.querySelector("[data-preview-result]"),
  };
  let timer = null;
  let lastSent = "";

  function show(which) {
    for (const [name, element] of Object.entries(panel)) element.hidden = name !== which;
  }

  // Put one value into every element marked data-out="<key>".
  function setText(key, value) {
    document.querySelectorAll(`[data-out="${key}"]`).forEach((el) => {
      el.textContent = value ?? "—";
    });
  }

  function render(data) {
    if (!data.ready) return show("empty");
    setText("department", data.department || data.category || "—");
    setText("category", data.department && data.category ? `(${data.category})` : "");
    setText("confidence", data.confidence ?? 0);
    document.querySelector('[data-out="confidence-bar"]').style.width = `${data.confidence ?? 0}%`;
    setText("urgency_label", data.urgency_label);
    setText("language", data.language);
    setText("location", data.location || "—");

    const urgency = document.querySelector('[data-out="urgency_label"]');
    urgency.className = `urgency-${data.urgency}`;

    const warning = document.querySelector('[data-out="warning"]');
    warning.hidden = data.allowed;
    warning.textContent = data.allowed ? "" : data.warning;

    document.querySelector('[data-out-show="similar_reported"]').hidden = !data.similar_reported;
    show("result");
  }

  async function updatePreview() {
    const body = new FormData(form); // includes the CSRF token, title, description, location
    const key = `${body.get("title")}|${body.get("description")}|${body.get("location")}`;
    if (key === lastSent) return;
    lastSent = key;
    if ((body.get("title") + body.get("description")).trim().length < 10) return show("empty");

    show("loading");
    try {
      const response = await fetch(form.dataset.previewUrl, { method: "POST", body, credentials: "same-origin" });
      if (response.ok) render(await response.json());
    } catch (err) {
      console.warn("Preview failed:", err); // the preview is only a helper; submitting still works
    }
  }

  // Wait until the student pauses typing for 600 ms (fewer requests).
  form.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(updatePreview, 600);
  });
}

// ---------------- 2. Voice input ----------------
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const mic = document.querySelector("[data-mic]");

if (mic && SpeechRecognition) {
  const LOCALES = { en: "en-IN", ta: "ta-IN", ml: "ml-IN" }; // follow the page language
  const textarea = mic.parentElement.querySelector("textarea");
  const label = mic.querySelector("span");
  const recognition = new SpeechRecognition();
  recognition.lang = LOCALES[mic.dataset.lang] || "en-IN";
  recognition.interimResults = false;
  recognition.continuous = false;
  let listening = false;

  mic.hidden = false;

  mic.addEventListener("click", () => {
    if (listening) return recognition.stop();
    recognition.start();
  });

  recognition.addEventListener("start", () => {
    listening = true;
    mic.classList.add("listening");
    label.textContent = T.listening || "Listening…";
  });

  recognition.addEventListener("end", () => {
    listening = false;
    mic.classList.remove("listening");
    label.textContent = T.speak || "Speak";
  });

  recognition.addEventListener("result", (event) => {
    const spoken = Array.from(event.results).map((r) => r[0].transcript).join(" ");
    textarea.value = (textarea.value ? `${textarea.value.trim()} ` : "") + spoken;
    textarea.dispatchEvent(new Event("input", { bubbles: true })); // refresh the AI preview
  });
}
