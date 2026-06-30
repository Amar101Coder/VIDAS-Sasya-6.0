document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("input");
    const output = document.getElementById("output");

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
        output.style.fontFamily =
          "'OpenDyslexic', 'OpenDyslexicRegular', sans-serif";
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
       COPY OUTPUT (BULLETPROOF)
    ===================== */
    document.getElementById("copy-btn").onclick = () => {
        const text = output.innerText.trim();
        if (!text) return;

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
        const selection = window.getSelection().toString();
        const text = selection || output.innerText || input.innerText;
        if (!text) return;

        speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text);
        u.rate = 1;
        u.pitch = 1;
        speechSynthesis.speak(u);
    };

    /* =====================
       BACKEND TTS (pyttsx3)
    ===================== */
    document.getElementById("backend-tts-btn").onclick = async () => {
        const text = output.innerText || input.innerText;
        if (!text) return;

        await fetch("/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
        });
    };
});
