function filterKeyspaces() {
    const filterValue = document.getElementById('keyspace-filter').value.toLowerCase();
    const items = document.querySelectorAll('.keyspace-item');

    items.forEach(item => {
        const name = item.dataset.name.toLowerCase();
        item.style.display = name.includes(filterValue) ? '' : 'none';
    });

    // Also filter the graph if clusterData is available
    if (typeof clusterData !== 'undefined' && typeof renderTopologyGraph === 'function') {
        const filteredKeyspaces = clusterData.keyspaces.filter(ks =>
            ks.name.toLowerCase().includes(filterValue)
        );
        const filteredData = {
            ...clusterData,
            metrics: { ...clusterData.metrics },
            keyspaces: filteredKeyspaces
        };
        renderTopologyGraph(filteredData);
    }
}

function formatReplication(replicationStr) {
    try {
        // Try to parse if it's a JSON-like string from python repr
        let clean = replicationStr.replace(/'/g, '"');
        let obj = JSON.parse(clean);
        let strategy = obj.class || 'Unknown';
        if (strategy.includes('.')) {
            strategy = strategy.split('.').pop();
        }

        let details = [];
        for (let key in obj) {
            if (key !== 'class') {
                details.push(`${key}: ${obj[key]}`);
            }
        }
        return details.length > 0 ? `${strategy} (${details.join(', ')})` : strategy;
    } catch (e) {
        return replicationStr;
    }
}

function showKeyspaceDetail(item) {
    const detail = document.getElementById('keyspace-detail');
    const name = item.dataset.name;
    const replication = formatReplication(item.dataset.replication);
    const tables = item.dataset.tablecount;
    const durable = item.dataset.durable;
    const isVirtual = item.dataset.virtual;

    document.querySelectorAll('.keyspace-item').forEach(el => el.classList.remove('active'));
    item.classList.add('active');

    detail.innerHTML = `
        <div class="detail-header">
            <div class="title-group">
                <h3>${name}</h3>
                ${isVirtual === 'True' ? '<span class="badge virtual">Virtual</span>' : ''}
            </div>
            <a href="/cluster/${clusterConfigName}/keyspace/${name}" class="btn-primary">View Details</a>
        </div>
        
        <div class="detail-grid">
            <div class="detail-card">
                <span class="label">Replication Strategy</span>
                <span class="value code">${replication}</span>
            </div>
            <div class="detail-card">
                <span class="label">Tables</span>
                <span class="value accent">${tables}</span>
            </div>
            <div class="detail-card">
                <span class="label">Durable Writes</span>
                <span class="value">${durable === 'True' ? 'Enabled' : 'Disabled'}</span>
            </div>
        </div>
    `;
}

document.addEventListener('DOMContentLoaded', () => {
    if (typeof clusterData !== "undefined") {
        renderTopologyGraph(clusterData);
    }

    const filterInput = document.getElementById('keyspace-filter');
    if (filterInput) {
        filterInput.addEventListener('input', filterKeyspaces);
    }

    document.querySelectorAll('.keyspace-item').forEach(item => {
        item.addEventListener('click', () => showKeyspaceDetail(item));
    });
});


