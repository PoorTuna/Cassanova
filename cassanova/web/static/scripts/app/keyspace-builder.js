document.addEventListener('DOMContentLoaded', () => {
    const main = document.querySelector('.builder-page');
    const clusterName = main.dataset.cluster;

    // Inputs
    const ksNameInput = document.getElementById('keyspace-name');
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

    let datacenters = [];

    // --- State Management ---
    function updateState() {
        const name = ksNameInput.value.trim();
        const strategy = strategySelect.value;
        const rf = simpleStrategyRF.value;
        const durable = durableWritesSelect.value;

        let cql = `CREATE KEYSPACE IF NOT EXISTS "${name || 'keyspace_name'}"\n`;

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
        createBtn.disabled = !name;

        // Safety analysis
        analyzeSafety(strategy, rf);
    }

    function analyzeSafety(strategy, rf) {
        if (strategy === 'SimpleStrategy') {
            if (rf < 3) {
                safetyReport.innerHTML = `<span class="warning">⚠️ Replication factor < 3 is risky for production availability.</span>`;
            } else {
                safetyReport.textContent = `A replication factor of ${rf} provides standard high availability.`;
            }
        } else {
            if (datacenters.length === 0) {
                safetyReport.innerHTML = `<span class="warning">⚠️ Define at least one DC for NetworkTopologyStrategy.</span>`;
            } else {
                safetyReport.textContent = `NetworkTopologyStrategy is recommended for multi-datacenter deployments.`;
            }
        }
    }

    // --- Datacenter Management ---
    function addDatacenter(name = 'dc1', rf = 3) {
        const id = Date.now();
        const dcObj = { id, name, rf };
        datacenters.push(dcObj);

        const row = document.createElement('div');
        row.className = 'datacenter-row';
        row.dataset.id = id;
        row.innerHTML = `
            <input type="text" class="dc-name" value="${name}" placeholder="DC Name">
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
        confirmExecuteBtn.textContent = 'Deploying...';

        try {
            const response = await fetch(`/api/v1/cluster/${clusterName}/operations/cqlsh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    cql: cqlPreview.textContent
                })
            });

            const result = await response.json();
            if (response.ok) {
                Toast.success("Keyspace deployed successfully!");
                setTimeout(() => {
                    window.location.href = `/cluster/${clusterName}/keyspace/${ksNameInput.value.trim()}`;
                }, 1500);
            } else {
                Toast.error(`Deployment failed: ${result.detail || 'Unknown error'}`);
                confirmExecuteBtn.disabled = false;
                confirmExecuteBtn.textContent = 'Confirm & Deploy';
            }
        } catch (err) {
            Toast.error(`Error: ${err.message}`);
            confirmExecuteBtn.disabled = false;
            confirmExecuteBtn.textContent = 'Confirm & Deploy';
        }
    });

    // Initial state
    updateState();
});
