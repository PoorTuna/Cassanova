document.addEventListener("DOMContentLoaded", () => {
    const filterInput = document.getElementById("node-filter");
    const nodeCards = document.querySelectorAll(".node-card");

    filterInput.addEventListener("input", () => {
        const query = filterInput.value.toLowerCase();
        nodeCards.forEach(card => {
            const text = card.innerText.toLowerCase();
            card.style.display = text.includes(query) ? "" : "none";
        });
    });
});