function scrollKeyspaces(direction) {
    const carousel = document.getElementById('keyspace-carousel');
    const cardWidth = carousel.querySelector('.keyspace-card').offsetWidth + 20;
    carousel.scrollBy({
        left: direction * cardWidth,
        behavior: 'smooth'
    });
}

function filterKeyspaces() {
    const filterValue = document.getElementById('keyspace-filter').value.toLowerCase();

    const cards = document.querySelectorAll('.keyspace-card');
    cards.forEach(card => {
        let keyspaceName = card.querySelector('h3').innerText.toLowerCase();
        keyspaceName = keyspaceName.replace(/^keyspace:\s*/, '');
        if (keyspaceName.includes(filterValue)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });

    if (!window.originalClusterData) return;

    const filteredCluster = {
        ...window.originalClusterData,
        keyspaces: window.originalClusterData.keyspaces.filter(ks =>
            ks.name.toLowerCase().includes(filterValue)
        )
    };

    renderTopologyGraph(filteredCluster);
}

document.addEventListener('DOMContentLoaded', () => {
    const dataEl = document.getElementById('cluster-data');
    if (!dataEl) {
        console.error('Cluster data element missing');
        return;
    }
    window.originalClusterData = JSON.parse(dataEl.textContent);
    renderTopologyGraph(window.originalClusterData);

    document.getElementById('keyspace-filter').addEventListener('input', filterKeyspaces);
    document.querySelector('.carousel-btn.left').addEventListener('click', () => scrollKeyspaces(-1));
    document.querySelector('.carousel-btn.right').addEventListener('click', () => scrollKeyspaces(1));
});
