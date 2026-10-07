// Ventana emergente de la página de horarios.
// Cada grado es un <dialog id="horario-N">. El enlace de la cuadrícula
// (#horario-N) lo abre, así que también se puede compartir la dirección.
(() => {
    const dialogs = Array.from(document.querySelectorAll("dialog.ScheduleDialog"));
    if (!dialogs.length) return;

    const closeAll = () => dialogs.forEach((d) => d.open && d.close());

    const openFromHash = () => {
        const id = decodeURIComponent(location.hash.slice(1));
        const target = id ? document.getElementById(id) : null;
        if (target && target.matches("dialog.ScheduleDialog") && !target.open) {
            closeAll();
            target.showModal();
        }
    };

    dialogs.forEach((dialog) => {
        // Clic en el fondo oscuro (el propio <dialog>, no su contenido)
        dialog.addEventListener("click", (event) => {
            if (event.target === dialog) dialog.close();
        });

        const closeButton = dialog.querySelector("[data-close]");
        if (closeButton) closeButton.addEventListener("click", () => dialog.close());

        // Al cerrar (botón, Esc o fondo) se limpia la dirección para poder volver a abrirlo
        dialog.addEventListener("close", () => {
            if (location.hash === "#" + dialog.id) {
                history.replaceState(null, "", location.pathname + location.search);
            }
        });
    });

    window.addEventListener("hashchange", openFromHash);
    openFromHash();
})();