// Biblioteca: filtros que se aplican solos y formulario de materiales.
(() => {
    // Los filtros (grado, periodo, tipo) buscan al cambiar
    document.querySelectorAll("form[data-autosubmit]").forEach((form) => {
        form.querySelectorAll("select").forEach((s) => s.addEventListener("change", () => form.requestSubmit()));
    });

    // Formulario: solo se muestran los grupos del ciclo del área elegida
    const datos = document.getElementById("mapa-ciclos");
    const area = document.getElementById("id_area");
    if (!datos || !area) return;

    const mapa = JSON.parse(datos.textContent);
    const chips = document.querySelectorAll(".GroupChip");
    const bloque = document.getElementById("BloqueGrupos");
    const nota = document.getElementById("NotaTransversal");

    const actualizar = () => {
        const info = mapa.areas[area.value];
        const transversal = !!info && info.transversal;
        bloque.hidden = transversal;
        nota.hidden = !transversal;

        chips.forEach((chip) => {
            const ciclo = mapa.grupos[chip.dataset.grupo];
            const oculto = !info || (!transversal && ciclo !== info.ciclo);
            chip.hidden = oculto;
            if (oculto) chip.querySelector("input").checked = false;
        });
    };

    area.addEventListener("change", actualizar);
    actualizar();
})();