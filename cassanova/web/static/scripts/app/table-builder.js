document.addEventListener('DOMContentLoaded', () => {
    const builder = document.querySelector('.builder-page');
    const cluster = builder.dataset.cluster;
    const keyspace = builder.dataset.keyspace;

    const tableNameInput = document.getElementById('table-name');
    const columnsList = document.getElementById('columns-list');
    const addColumnBtn = document.getElementById('add-column-btn');
    const cqlPreview = document.getElementById('cql-preview');
    const safetyReport = document.getElementById('safety-report');
    const createTableBtn = document.getElementById('create-table-btn');

    const compactionSelect = document.getElementById('compaction-strategy');
    const ttlInput = document.getElementById('default-ttl');

    const executeModal = document.getElementById('execute-modal');
    const confirmExecuteBtn = document.getElementById('confirm-execute-btn');
    const finalCqlConfirm = document.getElementById('final-cql-confirm');

    const cassandraTypes = [
        'ascii', 'bigint', 'blob', 'boolean', 'counter', 'date',
        'decimal', 'double', 'duration', 'float', 'inet', 'int',
        'smallint', 'text', 'time', 'timestamp', 'timeuuid',
        'tinyint', 'uuid', 'varchar', 'varint'
    ];

    let columns = [
        { name: 'id', type: 'uuid', isPK: true, isCK: false },
        { name: 'created_at', type: 'timestamp', isPK: false, isCK: true },
        { name: 'data', type: 'text', isPK: false, isCK: false }
    ];

    function renderColumns() {
        columnsList.innerHTML = columns.map((col, idx) => `
            <div class="column-row" data-index="${idx}">
                <input type="text" value="${col.name}" placeholder="Column Name" class="col-name-input" autocomplete="off">
                <select class="col-type-select">
                    ${cassandraTypes.map(t => `<option value="${t}" ${col.type === t ? 'selected' : ''}>${t}</option>`).join('')}
                </select>
                <label class="pill-checkbox ${col.isPK ? 'active' : ''}">
                    <input type="checkbox" class="col-pk-check" ${col.isPK ? 'checked' : ''}>
                    <span>PK</span>
                </label>
                <label class="pill-checkbox ${col.isCK ? 'active' : ''}">
                    <input type="checkbox" class="col-ck-check" ${col.isCK ? 'checked' : ''}>
                    <span>CK</span>
                </label>
                <button class="btn-icon-danger remove-col-btn" title="Remove Column" ${columns.length <= 1 ? 'disabled' : ''}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"></path>
                    </svg>
                </button>
            </div>
        `).join('');

        attachColumnEvents();
        updatePreview();
    }

    function attachColumnEvents() {
        const rows = columnsList.querySelectorAll('.column-row');
        rows.forEach(row => {
            const idx = parseInt(row.dataset.index);

            row.querySelector('.col-name-input').addEventListener('input', (e) => {
                columns[idx].name = e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '');
                e.target.value = columns[idx].name;
                updatePreview();
            });

            row.querySelector('.col-type-select').addEventListener('change', (e) => {
                columns[idx].type = e.target.value;
                updatePreview();
            });

            row.querySelector('.col-pk-check').addEventListener('change', (e) => {
                columns[idx].isPK = e.target.checked;
                if (e.target.checked) {
                    columns[idx].isCK = false; // PK can't be CK
                }
                renderColumns();
            });

            row.querySelector('.col-ck-check').addEventListener('change', (e) => {
                columns[idx].isCK = e.target.checked;
                if (e.target.checked) {
                    columns[idx].isPK = false; // CK can't be PK
                }
                renderColumns();
            });

            row.querySelector('.remove-col-btn')?.addEventListener('click', () => {
                columns.splice(idx, 1);
                renderColumns();
            });
        });
    }

    function generateCQL() {
        const tableName = tableNameInput.value.trim() || 'unset_table_name';
        const pkCols = columns.filter(c => c.isPK).map(c => c.name);
        const ckCols = columns.filter(c => c.isCK).map(c => c.name);

        if (pkCols.length === 0) return "-- Error: Missing Partition Key (PK)";

        let cql = `CREATE TABLE "${keyspace}"."${tableName}" (\n`;

        // Definitions
        columns.forEach(col => {
            cql += `  ${col.name} ${col.type},\n`;
        });

        // Primary Key Construction
        const pkString = pkCols.length > 1 ? `(${pkCols.join(', ')})` : pkCols[0];
        const fullPK = ckCols.length > 0 ? `(${pkString}, ${ckCols.join(', ')})` : `(${pkString})`;

        cql += `  PRIMARY KEY ${fullPK}\n`;
        cql += `)`;

        // Options
        let options = [];
        if (compactionSelect.value) {
            options.push(`compaction = {'class': '${compactionSelect.value}'}`);
        }
        if (ttlInput.value && ttlInput.value > 0) {
            options.push(`default_time_to_live = ${ttlInput.value}`);
        }

        if (options.length > 0) {
            cql += ` WITH ${options.join('\n  AND ')};`;
        } else {
            cql += `;`;
        }

        return cql;
    }

    function updatePreview() {
        const cql = generateCQL();
        cqlPreview.textContent = cql;

        const isValid = tableNameInput.value.trim().length > 0 &&
            columns.some(c => c.isPK) &&
            columns.every(c => c.name.length > 0);

        createTableBtn.disabled = !isValid;
        analyzeSafety();
    }

    function analyzeSafety() {
        const pk = columns.filter(c => c.isPK);
        const ck = columns.filter(c => c.isCK);

        if (tableNameInput.value.trim().length === 0) {
            safetyReport.innerHTML = "Specify a table name.";
            safetyReport.className = "safety-message";
            return;
        }

        if (pk.length === 0) {
            safetyReport.innerHTML = "⚠️ Table must have at least one <strong>Partition Key (PK)</strong>.";
            safetyReport.className = "safety-message warning";
            return;
        }

        let findings = [];

        // Cardinality check
        if (pk.length === 1 && (pk[0].type === 'text' || pk[0].type === 'uuid')) {
            findings.push("✅ Standard distribution detected for " + pk[0].name + " partition.");
        }

        if (pk.length > 0 && pk.some(p => p.type === 'boolean')) {
            findings.push("❌ <strong>High risk detected:</strong> Partitioning on a boolean field will create a massive hot-spot (only 2 partitions total).");
        }

        if (findings.length === 0) {
            safetyReport.innerHTML = "Schema looks healthy. Ready to deploy.";
            safetyReport.className = "safety-message";
        } else {
            safetyReport.innerHTML = findings.join('<br>');
            safetyReport.className = "safety-message " + (findings.some(f => f.includes('risk')) ? 'warning' : '');
        }
    }

    addColumnBtn.addEventListener('click', () => {
        columns.push({ name: 'new_col_' + columns.length, type: 'text', isPK: false, isCK: false });
        renderColumns();
    });

    tableNameInput.addEventListener('input', updatePreview);
    compactionSelect.addEventListener('change', updatePreview);
    ttlInput.addEventListener('input', updatePreview);

    createTableBtn.addEventListener('click', () => {
        finalCqlConfirm.textContent = generateCQL();
        executeModal.classList.remove('hidden');
    });

    confirmExecuteBtn.addEventListener('click', async () => {
        const cql = generateCQL();
        try {
            confirmExecuteBtn.disabled = true;
            confirmExecuteBtn.textContent = 'Executing...';

            const response = await fetch(`/api/v1/cluster/${cluster}/operations/cqlsh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cql: cql })
            });

            if (response.ok) {
                Toast.success("Table created successfully!");
                setTimeout(() => {
                    window.location.href = `/cluster/${cluster}/keyspace/${keyspace}`;
                }, 1500);
            } else {
                const err = await response.json();
                Toast.error("Failed to create table: " + (err.detail || "Unknown error"));
            }
        } catch (e) {
            Toast.error("Execution failed: " + e.message);
        } finally {
            confirmExecuteBtn.disabled = false;
            confirmExecuteBtn.textContent = 'Confirm & Create';
        }
    });

    // Modal Close
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            if (modal) modal.classList.add('hidden');
        });
    });

    // Initial Render
    renderColumns();
});
