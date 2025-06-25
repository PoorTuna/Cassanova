// Toggle dropdown menu visibility, close others
function toggleDropdown(event) {
    event.stopPropagation();

    const button = event.currentTarget;
    const menu = button.nextElementSibling;

    // Close all other dropdowns except this one
    document.querySelectorAll('.dropdown-menu').forEach(otherMenu => {
        if (otherMenu !== menu) {
            otherMenu.classList.add('hidden');
        }
    });

    menu.classList.toggle('hidden');
}

// Close all dropdown menus
function closeAllDropdowns() {
    document.querySelectorAll('.dropdown-menu').forEach(menu => menu.classList.add('hidden'));
}

function deleteTable(clusterName, keyspaceName, table) {
    fetch(`/api/v1/cluster/${encodeURIComponent(clusterName)}/keyspace/${encodeURIComponent(keyspaceName)}/table/${encodeURIComponent(table)}`, {
        method: 'DELETE',
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(error => {
                    throw new Error(error.detail || response.statusText);
                });
            }
            return response.json();
        })
        .then(() => {
            window.location.reload();
        })
        .catch(err => {
            alert(`Delete failed: ${err.message}`);
        });
}

function truncateTable(clusterName, keyspaceName, table) {
    fetch(`/api/v1/cluster/${encodeURIComponent(clusterName)}/keyspace/${encodeURIComponent(keyspaceName)}/table/${encodeURIComponent(table)}/truncate`, {
        method: 'DELETE',
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(error => {
                    throw new Error(error.detail || response.statusText);
                });
            }
            return response.json();
        })
        .then(() => {
            window.location.reload();
        })
        .catch(err => {
            alert(`Truncate failed: ${err.message}`);
        });
}

function showTableDescription(clusterName, keyspaceName, table) {
    fetch(`/api/v1/cluster/${encodeURIComponent(clusterName)}/keyspace/${encodeURIComponent(keyspaceName)}/table/${encodeURIComponent(table)}/description`, {
        method: 'GET',
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(error => {
                    throw new Error(error.detail || response.statusText);
                });
            }
            return response.json();
        })
        .then(data => {
            showModal(data);
        })
        .catch(err => {
            alert(`Truncate failed: ${err.message}`);
        });
}

function showTableSchema(clusterName, keyspaceName, table) {
    fetch(`/api/v1/cluster/${encodeURIComponent(clusterName)}/keyspace/${encodeURIComponent(keyspaceName)}/table/${encodeURIComponent(table)}/schema`, {
        method: 'GET',
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(error => {
                    throw new Error(error.detail || response.statusText);
                });
            }
            return response.json();
        })
        .then(data => {
            showModal(data);
        })
        .catch(err => {
            alert(`Truncate failed: ${err.message}`);
        });
}


// Close dropdowns when clicking outside
document.addEventListener('click', closeAllDropdowns);

// Setup event listeners after DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Attach toggleDropdown to all .table-options-btn buttons (no inline onclick)
    document.querySelectorAll('.table-options-btn').forEach(button => {
        button.addEventListener('click', toggleDropdown);
    });
    document.getElementById('modal-close').addEventListener('click', hideModal);
    document.getElementById('json-modal').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) hideModal();
    });
    // Dropdown menu button actions
    document.querySelectorAll('.dropdown-menu button').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const action = e.target.dataset.action;
            const table = e.target.dataset.table;
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

    // Filter input for tables
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
});


function showModal(jsonData) {
    const modal = document.getElementById('json-modal');
    const pre = document.getElementById('modal-pre');
    pre.textContent = JSON.stringify(jsonData, null, 2);
    modal.classList.remove('hidden');
}

function hideModal() {
    const modal = document.getElementById('json-modal');
    modal.classList.add('hidden');
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

document.getElementById('confirm-action-btn').addEventListener('click', () => {
    if (confirmCallback) confirmCallback();
    closeConfirmModal();
});