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

function showKeyspaceDetail(item) {
    const detail = document.getElementById('keyspace-detail');
    const name = item.dataset.name;
    const replication = item.dataset.replication;
    const tables = item.dataset.tablecount;
    const durable = item.dataset.durable;
    const isVirtual = item.dataset.virtual;

    document.querySelectorAll('.keyspace-item').forEach(el => el.classList.remove('active'));
    item.classList.add('active');

    detail.innerHTML = `
        <h3>${name}</h3>
        <p><strong>Replication:</strong> ${replication}</p>
        <p><strong>Tables:</strong> ${tables}</p>
        <p><strong>Durable Writes:</strong> ${durable}</p>
        <p><strong>Virtual:</strong> ${isVirtual}</p>
    `;
}

document.addEventListener('DOMContentLoaded', () => {
    if (typeof clusterData !== "undefined") {
        renderTopologyGraph(clusterData);
    }

    document.getElementById('keyspace-filter')
        .addEventListener('input', filterKeyspaces);

    document.querySelectorAll('.keyspace-item').forEach(item => {
        item.addEventListener('click', () => showKeyspaceDetail(item));
    });

    document.querySelectorAll('.keyspace-item').forEach(item => {
        item.addEventListener('click', () => {
            const name = item.dataset.name;
            const replication = item.dataset.replication;
            const tableCount = item.dataset.tablecount;
            const durable = item.dataset.durable;
            const isVirtual = item.dataset.virtual;

            const detail = document.getElementById('keyspace-detail');
            detail.innerHTML = `
            <h3>${name}</h3>
            <p>Replication: ${replication}</p>
            <p>Tables: ${tableCount}</p>
            <p>Durable Writes: ${durable}</p>
            <p>Virtual: ${isVirtual}</p>
            <a href="/cluster/${clusterConfigName}/keyspace/${name}" class="button">View Details</a>
        `;
        });
    });
});


