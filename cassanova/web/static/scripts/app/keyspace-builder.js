document.addEventListener('DOMContentLoaded', () => {
    const main = document.querySelector('.builder-page');
    const clusterName = main.dataset.cluster;
    const mode = main.dataset.mode || 'create';
    const existingKeyspace = main.dataset.existingKeyspace
        ? JSON.parse(main.dataset.existingKeyspace)
        : null;

    // Inputs
    const ksNameInput = document.getElementById('keyspace-name');
    const ksNameError = document.getElementById('ks-name-error');
    const durableWritesSelect = document.getElementById('durable-writes');
    const strategySelect = document.getElementById('replication-strategy');
    const simpleStrategyRF = document.getElementById('replication-factor');
    const dcListContainer = document.getElementById('dc-list');
    const addDcBtn = document.getElementById('add-dc-btn');

    // UI Elements
    const simpleStrategyOptions = document.getElementById('simple-strategy-options');
    const networkTopologyOptions = document.getElementById('network-topology-options');
    const strategyInfo = document.getElementById('strategy-info');
    const cqlPreview = document.getElementById('cql-preview');
    const createBtn = document.getElementById('create-keyspace-btn');
    const safetyReport = document.getElementById('safety-report');

    // Modals
    const executeModal = document.getElementById('execute-modal');
    const finalCqlConfirm = document.getElementById('final-cql-confirm');
    const confirmExecuteBtn = document.getElementById('confirm-execute-btn');
    const closeModalBtns = document.querySelectorAll('.close-modal');

    const CQL_RESERVED = new Set([
        'add', 'allow', 'alter', 'and', 'apply', 'asc', 'authorize', 'batch',
        'begin', 'by', 'columnfamily', 'create', 'delete', 'desc', 'describe',
        'drop', 'entries', 'execute', 'from', 'full', 'grant', 'if', 'in',
        'index', 'infinity', 'insert', 'into', 'keyspace', 'limit', 'modify',
        'nan', 'norecursive', 'not', 'null', 'of', 'on', 'or', 'order',
        'primary', 'rename', 'replace', 'revoke', 'schema', 'select', 'set',
        'table', 'to', 'token', 'truncate', 'unlogged', 'update', 'use',
        'using', 'where', 'with'
    ]);

    let datacenters = [];

    function validateKsName(name) {
        if (!name) return '';
        if (/^\d/.test(name)) return 'Name cannot start with a digit';
        if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name)) return 'Only alphanumeric and underscore allowed';
        if (name.length > 48) return 'Name too long (max 48 chars)';
        if (CQL_RESERVED.has(name.toLowerCase())) return `"${name}" is a CQL reserved word`;
        return '';
    }

    function updateState() {
        const name = ksNameInput.value.trim();
        const strategy = strategySelect.value;
        const rf = simpleStrategyRF.value;
        const durable = durableWritesSelect.value;

        // Validate name
        const nameErr = validateKsName(name);
        if (nameErr) {
            ksNameError.textContent = nameErr;
            ksNameError.classList.remove('hidden');
        } else {
            ksNameError.classList.add('hidden');
        }

        const verb = mode === 'alter' ? 'ALTER' : 'CREATE';
        const ifne = mode === 'alter' ? '' : ' IF NOT EXISTS';
        let cql = `${verb} KEYSPACE${ifne} "${name || 'keyspace_name'}"\n`;

        if (strategy === 'SimpleStrategy') {
            cql += `WITH REPLICATION = {\n  'class': 'SimpleStrategy',\n  'replication_factor': ${rf || 1}\n}`;
        } else {
            cql += `WITH REPLICATION = {\n  'class': 'NetworkTopologyStrategy'`;
            datacenters.forEach(dc => {
                if (dc.name && dc.rf) {
                    cql += `,\n  '${dc.name}': ${dc.rf}`;
                }
            });
            cql += `\n}`;
        }

        if (durable === 'false') {
            cql += `\nAND DURABLE_WRITES = false;`;
        } else {
            cql += `;`;
        }

        cqlPreview.textContent = cql;
        createBtn.disabled = !name || !!nameErr;

        analyzeSafety(strategy, rf);
    }

    function analyzeSafety(strategy, rf) {
        if (strategy === 'SimpleStrategy') {
            if (rf < 3) {
                safetyReport.innerHTML = `<span class="warning">Replication factor < 3 is risky for production availability.</span>`;
            } else {
                safetyReport.textContent = `A replication factor of ${rf} provides standard high availability.`;
            }
        } else {
            if (datacenters.length === 0) {
                safetyReport.innerHTML = `<span class="warning">Define at least one DC for NetworkTopologyStrategy.</span>`;
            } else {
                const lowRf = datacenters.filter(dc => dc.rf && parseInt(dc.rf) < 3);
                if (lowRf.length > 0) {
                    safetyReport.innerHTML = `<span class="warning">DC "${escapeHtml(lowRf[0].name)}" has RF < 3. Consider increasing for production.</span>`;
                } else {
                    safetyReport.textContent = `NetworkTopologyStrategy with ${datacenters.length} DC(s). Production-ready.`;
                }
            }
        }
    }

    // --- Datacenter Management ---
    function addDatacenter(name = 'dc1', rf = 3) {
        const id = Date.now() + Math.random();
        const dcObj = { id, name, rf };
        datacenters.push(dcObj);

        const row = document.createElement('div');
        row.className = 'datacenter-row';
        row.dataset.id = id;
        row.innerHTML = `
            <input type="text" class="dc-name" value="${escapeHtml(name)}" placeholder="DC Name">
            <input type="number" class="dc-rf" value="${rf}" min="1" max="10">
            <button class="btn-icon-danger remove-dc-btn" title="Remove DC">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"></path>
                </svg>
            </button>
        `;

        const nameInput = row.querySelector('.dc-name');
        const rfInput = row.querySelector('.dc-rf');
        const removeBtn = row.querySelector('.remove-dc-btn');

        nameInput.addEventListener('input', () => {
            dcObj.name = nameInput.value;
            updateState();
        });

        rfInput.addEventListener('input', () => {
            dcObj.rf = rfInput.value;
            updateState();
        });

        removeBtn.addEventListener('click', () => {
            datacenters = datacenters.filter(d => d.id !== id);
            row.remove();
            updateState();
        });

        dcListContainer.appendChild(row);
        updateState();
    }

    // --- Event Listeners ---
    ksNameInput.addEventListener('input', updateState);
    durableWritesSelect.addEventListener('change', updateState);
    simpleStrategyRF.addEventListener('input', updateState);

    strategySelect.addEventListener('change', () => {
        const val = strategySelect.value;
        if (val === 'SimpleStrategy') {
            simpleStrategyOptions.classList.remove('hidden');
            networkTopologyOptions.classList.add('hidden');
            strategyInfo.textContent = 'Use SimpleStrategy for small development clusters or single-DC setups.';
        } else {
            simpleStrategyOptions.classList.add('hidden');
            networkTopologyOptions.classList.remove('hidden');
            strategyInfo.textContent = 'Use NetworkTopologyStrategy for multi-datacenter or production cloud deployments.';
            if (datacenters.length === 0) {
                addDatacenter('datacenter1', 3);
            }
        }
        updateState();
    });

    addDcBtn.addEventListener('click', () => addDatacenter('', 3));

    // Modal logic
    createBtn.addEventListener('click', () => {
        finalCqlConfirm.textContent = cqlPreview.textContent;
        executeModal.classList.remove('hidden');
    });

    closeModalBtns.forEach(btn => {
        btn.addEventListener('click', () => executeModal.classList.add('hidden'));
    });

    confirmExecuteBtn.addEventListener('click', async () => {
        confirmExecuteBtn.disabled = true;
        confirmExecuteBtn.textContent = mode === 'alter' ? 'Applying...' : 'Deploying...';

        try {
            const response = await fetch(`/api/v1/cluster/${clusterName}/operations/cqlsh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cql: cqlPreview.textContent })
            });

            const result = await response.json();
            if (response.ok) {
                Toast.success(mode === 'alter' ? "Keyspace updated!" : "Keyspace deployed!");
                setTimeout(() => {
                    window.location.href = `/cluster/${clusterName}/keyspace/${ksNameInput.value.trim()}`;
                }, 1500);
            } else {
                Toast.error(`Failed: ${result.detail || 'Unknown error'}`);
                confirmExecuteBtn.disabled = false;
                confirmExecuteBtn.textContent = mode === 'alter' ? 'Confirm & Apply' : 'Confirm & Deploy';
            }
        } catch (err) {
            Toast.error(`Error: ${err.message}`);
            confirmExecuteBtn.disabled = false;
            confirmExecuteBtn.textContent = mode === 'alter' ? 'Confirm & Apply' : 'Confirm & Deploy';
        }
    });

    // --- ALTER mode: pre-populate from existing schema ---
    function loadExistingKeyspace() {
        if (!existingKeyspace) return;

        ksNameInput.value = existingKeyspace.name || '';

        if (existingKeyspace.durable_writes === false) {
            durableWritesSelect.value = 'false';
        }

        const strategy = existingKeyspace.strategy_class || '';
        if (strategy.includes('NetworkTopologyStrategy')) {
            strategySelect.value = 'NetworkTopologyStrategy';
            simpleStrategyOptions.classList.add('hidden');
            networkTopologyOptions.classList.remove('hidden');
            strategyInfo.textContent = 'Use NetworkTopologyStrategy for multi-datacenter or production cloud deployments.';

            const replication = existingKeyspace.replication || {};
            for (const [dc, rf] of Object.entries(replication)) {
                if (dc !== 'class') {
                    addDatacenter(dc, parseInt(rf));
                }
            }
        } else {
            strategySelect.value = 'SimpleStrategy';
            simpleStrategyRF.value = existingKeyspace.replication_factor || 3;
        }

        updateState();
    }

    // --- Initialize ---
    if (mode === 'alter') {
        loadExistingKeyspace();
    } else {
        updateState();
    }
});
