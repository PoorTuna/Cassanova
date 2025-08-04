// Generic fetch helper for table actions
async function performTableAction(cluster, keyspace, table, path = '', method = 'GET') {
    const url = `/api/v1/cluster/${encodeURIComponent(cluster)}/keyspace/${encodeURIComponent(keyspace)}/table/${encodeURIComponent(table)}${path}`;
    const response = await fetch(url, {method});
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || response.statusText);
    }
    return response.json();
}

// Specific actions using the generic helper
function deleteTable(cluster, keyspace, table) {
    return performTableAction(cluster, keyspace, table, '', 'DELETE')
        .then(() => window.location.reload())
        .catch(err => alert(`Delete failed: ${err.message}`));
}

function truncateTable(cluster, keyspace, table) {
    return performTableAction(cluster, keyspace, table, '/truncate', 'DELETE')
        .then(() => window.location.reload())
        .catch(err => alert(`Truncate failed: ${err.message}`));
}

function showTableDescription(cluster, keyspace, table) {
    return performTableAction(cluster, keyspace, table, '/description')
        .then(showModal)
        .catch(err => alert(`Show description failed: ${err.message}`));
}

function showTableSchema(cluster, keyspace, table) {
    return performTableAction(cluster, keyspace, table, '/schema')
        .then(showModal)
        .catch(err => alert(`Show schema failed: ${err.message}`));
}

// Modal functions
function showModal(jsonData) {
    const modal = document.getElementById('json-modal');
    const pre = document.getElementById('modal-pre');
    pre.textContent = JSON.stringify(jsonData, null, 2);
    modal.classList.remove('hidden');
}

function hideModal() {
    document.getElementById('json-modal').classList.add('hidden');
}

let confirmCallback = null;

function openConfirmModal(message, onConfirm) {
    document.getElementById('confirm-message').textContent = message;
    document.getElementById('confirm-modal').classList.remove('hidden');
    confirmCallback = onConfirm;
}

function closeConfirmModal() {
    document.getElementById('confirm-modal').classList.add('hidden');
    confirmCallback = null;
}


function toggleSection(elem) {
    const section = elem.nextElementSibling;
    section.classList.toggle('open');
}

// DOM setup
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('confirm-action-btn').addEventListener('click', () => {
        if (confirmCallback) confirmCallback();
        closeConfirmModal();
    });
    document.getElementById('modal-close').addEventListener('click', hideModal);
    document.getElementById('json-modal').addEventListener('click', e => {
        if (e.target === e.currentTarget) hideModal();
    });

    // Filter tables input
    const filterInput = document.getElementById('table-filter');
    const tables = document.querySelectorAll('.keyspace-card.table-card');
    if (filterInput) {
        filterInput.addEventListener('input', () => {
            const filter = filterInput.value.toLowerCase();
            tables.forEach(table => {
                const name = table.getAttribute('data-table').toLowerCase();
                table.style.display = name.includes(filter) ? 'block' : 'none';
            });
        });
    }

    // Manage each table options dropdown individually
    document.querySelectorAll('.table-options-btn').forEach(button => {
        const menu = button.nextElementSibling;
        let isOpen = false;

        function openMenu() {
            menu.classList.remove('hidden');
            isOpen = true;
            document.addEventListener('click', outsideClickListener);
        }

        function closeMenu() {
            menu.classList.add('hidden');
            isOpen = false;
            document.removeEventListener('click', outsideClickListener);
        }

        function toggleMenu(event) {
            event.stopPropagation();
            if (isOpen) closeMenu();
            else openMenu();
        }

        function outsideClickListener(event) {
            if (!button.contains(event.target) && !menu.contains(event.target)) {
                closeMenu();
            }
        }

        button.addEventListener('click', toggleMenu);
    });

    // Handle clicks on dropdown menu buttons
    document.querySelectorAll('.dropdown-menu button').forEach(btn => {
        btn.addEventListener('click', e => {
            const action = e.target.dataset.action;
            const table = e.target.dataset.table;
            if (!action || !table) return;

            if (action === 'description') {
                showTableDescription(clusterName, keyspaceName, table);
            } else if (action === 'schema') {
                showTableSchema(clusterName, keyspaceName, table);
            } else if (action === 'delete') {
                openConfirmModal(`Are you sure you want to delete table "${table}"? This cannot be undone.`, () => {
                    deleteTable(clusterName, keyspaceName, table);
                });
            } else if (action === 'truncate') {
                openConfirmModal(`Are you sure you want to truncate table "${table}"? This will remove all data.`, () => {
                    truncateTable(clusterName, keyspaceName, table);
                });
            }
        });
    });
});
