function openTableModal(tableName) {
    const modal = document.getElementById('table-modal');
    const title = document.getElementById('modal-title');
    title.textContent = `Table Actions: ${tableName}`;
    modal.classList.remove('hidden');
}

// Close modal on close btn or click outside modal content
document.querySelector('.modal-close').addEventListener('click', () => {
    document.getElementById('table-modal').classList.add('hidden');
});

window.addEventListener('click', (event) => {
    const modal = document.getElementById('table-modal');
    if (event.target === modal) {
        modal.classList.add('hidden');
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const filterInput = document.getElementById('table-filter');
    if (!filterInput) return;

    const tables = document.querySelectorAll('.keyspace-card.table-card');

    filterInput.addEventListener('input', () => {
        const filter = filterInput.value.toLowerCase();
        tables.forEach(table => {
            const name = table.getAttribute('data-table').toLowerCase();
            table.style.display = name.includes(filter) ? 'block' : 'none';
        });
    });
});