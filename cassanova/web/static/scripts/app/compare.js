document.addEventListener('DOMContentLoaded', () => {
    const tree = document.getElementById('diff-tree');
    const loading = document.getElementById('compare-loading');
    const summary = document.getElementById('compare-summary');
    const filter = document.getElementById('compare-filter');
    const hideIdentical = document.getElementById('hide-identical');

    // Picker navigation
    document.getElementById('compare-btn').addEventListener('click', () => {
        const a = document.getElementById('compare-select-a').value;
        const b = document.getElementById('compare-select-b').value;
        if (a === b) { Toast.error('Select two different clusters'); return; }
        window.location.href = `/compare/${encodeURIComponent(a)}/${encodeURIComponent(b)}`;
    });

    // Fetch diff data
    fetch(`/api/v1/compare/${encodeURIComponent(compareClusterA)}/${encodeURIComponent(compareClusterB)}`)
        .then(res => { if (!res.ok) throw new Error(res.statusText); return res.json(); })
        .then(data => renderDiff(data))
        .catch(err => {
            loading.textContent = `Failed to compare: ${err.message}`;
            loading.classList.add('error');
        });

    function renderDiff(data) {
        loading.remove();
        const ks = data.keyspaces;
        const names = Object.keys(ks).sort();

        let totalKs = names.length;
        let diffCount = names.filter(n => ks[n].status !== 'identical').length;
        summary.textContent = `${totalKs} keyspaces compared, ${diffCount} with differences`;

        if (names.length === 0) {
            tree.innerHTML = '<div class="compare-empty">No user keyspaces found.</div>';
            return;
        }

        const frag = document.createDocumentFragment();
        names.forEach(name => {
            frag.appendChild(buildKsNode(name, ks[name]));
        });
        tree.appendChild(frag);
        applyFilters();
    }

    function buildKsNode(name, ks) {
        const node = el('div', 'diff-node diff-ks');
        node.dataset.status = ks.status;
        node.dataset.name = name.toLowerCase();

        const header = el('div', 'diff-node-header');
        const toggle = el('span', 'diff-toggle');
        toggle.textContent = '\u25B6';
        const label = el('span', 'diff-label');
        label.textContent = name;
        const badge = el('span', `diff-badge badge-${ks.status}`);
        badge.textContent = statusLabel(ks.status);
        header.append(toggle, label, badge);

        if (ks.replication_a || ks.replication_b) {
            const detail = el('span', 'diff-detail');
            detail.textContent = `replication differs`;
            header.appendChild(detail);
        }

        node.appendChild(header);

        if (ks.tables) {
            const children = el('div', 'diff-children hidden');
            const tableNames = Object.keys(ks.tables).sort();
            tableNames.forEach(tName => {
                children.appendChild(buildTableNode(tName, ks.tables[tName]));
            });
            node.appendChild(children);

            header.style.cursor = 'pointer';
            header.addEventListener('click', () => {
                const open = !children.classList.contains('hidden');
                children.classList.toggle('hidden');
                toggle.textContent = open ? '\u25B6' : '\u25BC';
            });
        }

        return node;
    }

    function buildTableNode(name, tbl) {
        const node = el('div', 'diff-node diff-table');
        node.dataset.status = tbl.status;
        node.dataset.name = name.toLowerCase();

        const header = el('div', 'diff-node-header');
        const toggle = el('span', 'diff-toggle');
        toggle.textContent = '\u25B6';
        const label = el('span', 'diff-label');
        label.textContent = name;
        const badge = el('span', `diff-badge badge-${tbl.status}`);
        badge.textContent = statusLabel(tbl.status);
        header.append(toggle, label, badge);

        if (tbl.pk_a || tbl.pk_b) {
            const detail = el('span', 'diff-detail');
            detail.textContent = 'partition key differs';
            header.appendChild(detail);
        }

        node.appendChild(header);

        if (tbl.columns) {
            const children = el('div', 'diff-children hidden');
            const colNames = Object.keys(tbl.columns).sort();
            colNames.forEach(cName => {
                children.appendChild(buildColNode(cName, tbl.columns[cName]));
            });
            node.appendChild(children);

            header.style.cursor = 'pointer';
            header.addEventListener('click', (e) => {
                e.stopPropagation();
                const open = !children.classList.contains('hidden');
                children.classList.toggle('hidden');
                toggle.textContent = open ? '\u25B6' : '\u25BC';
            });
        }

        return node;
    }

    function buildColNode(name, col) {
        const node = el('div', 'diff-node diff-col');
        node.dataset.status = col.status;

        const header = el('div', 'diff-node-header');
        const spacer = el('span', 'diff-toggle-spacer');
        const label = el('span', 'diff-label');
        label.textContent = name;
        const badge = el('span', `diff-badge badge-${col.status}`);
        badge.textContent = statusLabel(col.status);
        header.append(spacer, label, badge);

        if (col.status === 'different') {
            const detail = el('span', 'diff-detail');
            detail.textContent = `${col.type_a} \u2192 ${col.type_b}`;
            header.appendChild(detail);
        } else if (col.status === 'only_a') {
            const detail = el('span', 'diff-detail');
            detail.textContent = col.type_a;
            header.appendChild(detail);
        } else if (col.status === 'only_b') {
            const detail = el('span', 'diff-detail');
            detail.textContent = col.type_b;
            header.appendChild(detail);
        } else {
            const detail = el('span', 'diff-detail');
            detail.textContent = col.type_a;
            header.appendChild(detail);
        }

        node.appendChild(header);
        return node;
    }

    function statusLabel(s) {
        return { only_a: 'Only A', only_b: 'Only B', different: 'Different', identical: 'Identical' }[s] || s;
    }

    function el(tag, className) {
        const e = document.createElement(tag);
        if (className) e.className = className;
        return e;
    }

    // Filtering
    function applyFilters() {
        const q = filter.value.toLowerCase();
        const hide = hideIdentical.checked;
        document.querySelectorAll('.diff-ks').forEach(node => {
            const name = node.dataset.name;
            const status = node.dataset.status;
            const matchesFilter = !q || name.includes(q);
            const matchesStatus = !hide || status !== 'identical';
            node.style.display = (matchesFilter && matchesStatus) ? '' : 'none';
        });
    }

    filter.addEventListener('input', applyFilters);
    hideIdentical.addEventListener('change', applyFilters);
});
