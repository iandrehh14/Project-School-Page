// Control de tamaño de texto.
// Pega este bloque en static/js/script.js (o cárgalo como archivo aparte).
(() => {
    const MIN = 0.85;
    const MAX = 1.5;
    const STEP = 0.1;
    const KEY = "textScale";
    const root = document.documentElement;

    const apply = (value) => {
        const clamped = Math.min(MAX, Math.max(MIN, Math.round(value * 100) / 100));
        root.style.setProperty("--text-scale", clamped);
        try { localStorage.setItem(KEY, clamped); } catch (e) { /* sin almacenamiento */ }
        return clamped;
    };

    let saved = 1;
    try { saved = parseFloat(localStorage.getItem(KEY)) || 1; } catch (e) { /* ignorar */ }
    let scale = apply(saved);

    document.querySelectorAll("[data-text-size]").forEach((button) => {
        button.addEventListener("click", () => {
            const action = button.dataset.textSize;
            if (action === "up") scale = apply(scale + STEP);
            else if (action === "down") scale = apply(scale - STEP);
            else scale = apply(1);
        });
    });
})();