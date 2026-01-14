async function performTableAction(cluster, keyspace, table, path = '', method = 'GET') {
    const url = `/api/v1/cluster/${encodeURIComponent(cluster)}/keyspace/${encodeURIComponent(keyspace)}/table/${encodeURIComponent(table)}${path}`;
    const response = await fetch(url, { method });
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || response.statusText);
    }
    return response.json();
}

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

/* ------------------- Modals ------------------- */
function showModal(jsonData) {
    const modal = document.getElementById('json-modal');
    const pre = document.getElementById('modal-pre');
    pre.innerHTML = syntaxHighlight(jsonData);
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

/* ------------------- Init ------------------- */
document.addEventListener('DOMContentLoaded', () => {
    /* Confirm Modal */
    document.getElementById('confirm-action-btn').addEventListener('click', () => {
        if (confirmCallback) confirmCallback();
        closeConfirmModal();
    });
    document.getElementById('modal-close').addEventListener('click', hideModal);
    document.getElementById('json-modal').addEventListener('click', e => {
        if (e.target === e.currentTarget) hideModal();
    });

    /* Table filter */
    const filterInput = document.getElementById('table-filter');
    const tableItems = document.querySelectorAll("#table-list .keyspace-item");
    if (filterInput) {
        filterInput.addEventListener("input", () => {
            const q = filterInput.value.toLowerCase();
            tableItems.forEach(item => {
                const name = item.getAttribute("data-name").toLowerCase();
                item.style.display = name.includes(q) ? "" : "none";
            });
        });
    }

    /* Table detail panel */
    const tableDetails = document.querySelectorAll("#table-detail .table-detail");
    const detailPanel = document.getElementById("table-detail");
    const placeholder = detailPanel.querySelector("p");

    tableItems.forEach(item => {
        item.addEventListener("click", () => {
            // highlight selected
            tableItems.forEach(i => i.classList.remove("active"));
            item.classList.add("active");

            // hide all details
            tableDetails.forEach(d => d.classList.add("hidden"));

            // show selected table
            const name = item.getAttribute("data-name");
            const detail = document.getElementById(`table-${name}`);
            if (detail) {
                if (placeholder) placeholder.style.display = "none";
                detail.classList.remove("hidden");
                detailPanel.scrollTop = 0;
            }
        });
    });

    /* Dropdown menus */
    document.querySelectorAll('.table-options-btn').forEach(button => {
        const menu = button.nextElementSibling;

        button.addEventListener('click', e => {
            e.stopPropagation();
            menu.classList.toggle('hidden');
        });

        document.addEventListener('click', e => {
            if (!button.contains(e.target) && !menu.contains(e.target)) {
                menu.classList.add('hidden');
            }
        });
    });

    /* Dropdown actions */
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
