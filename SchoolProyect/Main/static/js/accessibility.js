// Barra de accesibilidad: texto más grande, texto más pequeño y alto contraste.
// Se carga en el <head> de base.html para aplicar la preferencia guardada
// antes de que se pinte la página (así no hay "parpadeo"); la barra se crea sola.
(function () {
    "use strict";

    var MIN = 0.5;      // 50 %
    var MAX = 1.5;      // 150 %
    var STEP = 0.1;
    var KEY_SIZE = "a11y-text-scale";
    var KEY_CONTRAST = "a11y-contrast";
    var root = document.documentElement;

    function read(key) {
        try { return localStorage.getItem(key); } catch (e) { return null; }
    }
    function write(key, value) {
        try { localStorage.setItem(key, value); } catch (e) { /* sin almacenamiento */ }
    }
    function clamp(value) {
        return Math.min(MAX, Math.max(MIN, Math.round(value * 100) / 100));
    }

    var scale = parseFloat(read(KEY_SIZE));
    scale = isFinite(scale) ? clamp(scale) : 1;

    // Si la persona nunca eligió, se respeta la preferencia de contraste de su sistema
    var storedContrast = read(KEY_CONTRAST);
    var contrast = storedContrast === null
        ? !!(window.matchMedia && window.matchMedia("(prefers-contrast: more)").matches)
        : storedContrast === "1";

    // El tamaño se aplica al <html>: todo el sitio está en rem, así que escala completo
    // y además respeta el tamaño de letra que la persona ya tenga en su navegador.
    function applySize() {
        root.style.fontSize = (scale * 100) + "%";
    }
    function applyContrast() {
        if (contrast) root.setAttribute("data-contraste", "alto");
        else root.removeAttribute("data-contraste");
    }
    applySize();
    applyContrast();

    function build() {
        var bar = document.createElement("div");
        bar.className = "A11yBar";
        bar.setAttribute("role", "group");
        bar.setAttribute("aria-label", "Opciones de accesibilidad");
        bar.innerHTML =
            '<button type="button" class="A11yContrast" aria-pressed="false" aria-label="Alto contraste" title="Alto contraste">' +
                '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 18a6 6 0 0 0 0-12v12z" fill="currentColor"/></svg>' +
            '</button>' +
            '<button type="button" class="A11yDown" aria-label="Reducir tamaño del texto" title="Reducir texto">' +
                '<span aria-hidden="true">A<sup>&minus;</sup></span>' +
            '</button>' +
            '<button type="button" class="A11yUp" aria-label="Aumentar tamaño del texto" title="Aumentar texto">' +
                '<span aria-hidden="true">A<sup>+</sup></span>' +
            '</button>' +
            '<span class="A11yStatus" role="status" aria-live="polite"></span>';

        var btnContrast = bar.querySelector(".A11yContrast");
        var btnDown = bar.querySelector(".A11yDown");
        var btnUp = bar.querySelector(".A11yUp");
        var status = bar.querySelector(".A11yStatus");

        function refresh(message) {
            btnContrast.setAttribute("aria-pressed", contrast ? "true" : "false");
            btnDown.setAttribute("aria-disabled", scale <= MIN ? "true" : "false");
            btnUp.setAttribute("aria-disabled", scale >= MAX ? "true" : "false");
            if (message) status.textContent = message;
        }

        function changeSize(delta) {
            var next = clamp(scale + delta);
            if (next === scale) return;
            scale = next;
            write(KEY_SIZE, String(scale));
            applySize();
            refresh("Tamaño del texto: " + Math.round(scale * 100) + " %");
        }

        btnDown.addEventListener("click", function () { changeSize(-STEP); });
        btnUp.addEventListener("click", function () { changeSize(STEP); });
        btnContrast.addEventListener("click", function () {
            contrast = !contrast;
            write(KEY_CONTRAST, contrast ? "1" : "0");
            applyContrast();
            refresh(contrast ? "Alto contraste activado" : "Alto contraste desactivado");
        });

        refresh();
        document.body.appendChild(bar);
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build);
    else build();
})();