document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("input");
    const output = document.getElementById("output");
    const dyslexicFont = "'OpenDyslexic', 'OpenDyslexicRegular', sans-serif";

    function getReadableText() {
        const selection = window.getSelection().toString().trim();
        return selection || output.innerText.trim() || input.innerText.trim();
    }

    async function speakWithBackend(text) {
        const res = await fetch("/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
        });

        if (!res.ok) {
            throw new Error(await res.text());
        }
    }

    function speakInBrowser(text, options = {}) {
        if (!("speechSynthesis" in window) || !text) {
            return false;
        }

        if (options.interrupt !== false) {
            speechSynthesis.cancel();
        }

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = options.rate || 0.95;
        utterance.pitch = 1;
        utterance.volume = 1;

        const voices = speechSynthesis.getVoices();
        const englishVoice = voices.find(voice => voice.lang && voice.lang.toLowerCase().startsWith("en"));
        if (englishVoice) {
            utterance.voice = englishVoice;
        }

        speechSynthesis.resume();
        speechSynthesis.speak(utterance);
        return true;
    }

    if ("speechSynthesis" in window) {
        speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
        speechSynthesis.getVoices();
    }

    window.vidasSpeak = speakInBrowser;

    /* =====================
       THEME TOGGLE
    ===================== */
    document.getElementById("mode-toggle").onclick = () => {
        document.body.classList.toggle("light-mode");
    };

    /* =====================
       CLEAN COPY (NO INLINE STYLES, INPUT UNTOUCHED)
    ===================== */
    function cleanCopy() {
        const temp = document.createElement("div");
        temp.innerHTML = input.innerHTML;

        temp.querySelectorAll("*").forEach(el => {
            el.removeAttribute("style");
            el.removeAttribute("class");
        });

        return temp.innerHTML;
    }

    /* =====================
       FONT BUTTONS (OUTPUT ONLY)
    ===================== */
    document.getElementById("lexend-btn").onclick = () => {
        output.innerHTML = cleanCopy();
        output.style.fontFamily = "'Lexend', sans-serif";
    };

    document.getElementById("opendys-btn").onclick = () => {
        output.innerHTML = cleanCopy();
        output.style.fontFamily = dyslexicFont;
    };

    /* =====================
       SPACING CONTROLS (OUTPUT ONLY)
    ===================== */
    document.getElementById("letter-space").oninput = e =>
        output.style.letterSpacing = e.target.value + "px";

    document.getElementById("line-space").oninput = e =>
        output.style.lineHeight = e.target.value;

    document.getElementById("word-space").oninput = e =>
        output.style.wordSpacing = e.target.value + "px";

    /* =====================
       COPY OUTPUT WITH DYSLEXIC FONT
    ===================== */
    document.getElementById("copy-btn").onclick = async () => {
        const text = output.innerText.trim();
        if (!text) return;

        const html = `
            <div style="font-family: ${dyslexicFont}; letter-spacing: ${output.style.letterSpacing || "0px"}; line-height: ${output.style.lineHeight || "1.5"}; word-spacing: ${output.style.wordSpacing || "0px"}; white-space: pre-wrap;">
                ${output.innerHTML}
            </div>
        `;

        if (navigator.clipboard && window.ClipboardItem) {
            try {
                await navigator.clipboard.write([
                    new ClipboardItem({
                        "text/html": new Blob([html], { type: "text/html" }),
                        "text/plain": new Blob([text], { type: "text/plain" })
                    })
                ]);
                return;
            } catch (err) {
                console.error("Rich clipboard copy failed", err);
            }
        }

        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);

        ta.focus();
        ta.select();
        document.execCommand("copy");

        document.body.removeChild(ta);
    };

    /* =====================
       SIMPLIFY & HIGHLIGHT
    ===================== */
    async function simplifyRequest(text) {
        const res = await fetch("/simplify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
        });
        return res.json();
    }

    document.getElementById("simplify-btn").onclick = async () => {
        const data = await simplifyRequest(input.innerText);
        output.innerText = data.simplified;
    };

    document.getElementById("highlight-btn").onclick = async () => {
        const data = await simplifyRequest(input.innerText);
        output.innerHTML = data.highlighted;
    };

    /* =====================
       BROWSER TTS
    ===================== */
    document.getElementById("speak-btn").onclick = () => {
        const text = getReadableText();
        if (!text) return;

        if (!speakInBrowser(text)) {
            speakWithBackend(text).catch(err => console.error("Backend TTS failed", err));
        }
    };

    /* =====================
       BACKUP TTS
    ===================== */
    const backendTtsBtn = document.getElementById("backend-tts-btn");
    if (backendTtsBtn) {
      backendTtsBtn.onclick = async () => {
        const text = getReadableText();
        if (!text) return;

        if (!speakInBrowser(text)) {
            speakWithBackend(text).catch(err => console.error("Backend TTS failed", err));
        }
      };
    }
});
