const filterInput = document.getElementById('cluster-filter');
const clusterRows = document.querySelectorAll('.cluster-row');

filterInput.addEventListener('input', () => {
    const term = filterInput.value.trim().toLowerCase();
    clusterRows.forEach(row => {
        const name = row.dataset.name;
        row.hidden = !name.includes(term);
    });
});
