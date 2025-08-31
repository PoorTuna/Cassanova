window.originalClusterData = null;
window.network = null;

function renderTopologyGraph(cluster) {
    const nodes = [];
    const edges = [];

    nodes.push({
        id: 'cluster',
        label: cluster.metrics.name,
        shape: 'box',
        color: {
            background: '#121212',
            border: '#81d4fa',
            highlight: {
                background: '#1e1e1e',
                border: '#4fc3f7',
            }
        },
        font: {color: '#e0e0e0', highlight: {color: '#fff'}}
    });

    cluster.keyspaces.forEach((ks, i) => {
        const ksId = `ks-${i}`;
        nodes.push({
            id: ksId,
            label: ks.name,
            shape: 'box',
            color: {
                background: '#1e1e1e',
                border: '#4fc3f7',
                highlight: {
                    background: '#2a2a2a',
                    border: '#81d4fa',
                }
            },
            font: {color: '#81d4fa', highlight: {color: '#e0e0e0'}}
        });
        edges.push({from: 'cluster', to: ksId});

        ks.tables.forEach((table, j) => {
            const tableId = `ks-${i}-table-${j}`;
            nodes.push({
                id: tableId,
                label: table.name.length > 15 ? table.name.substring(0, 12) + '...' : table.name,
                shape: 'box',
                color: {
                    background: '#2a2a2a',
                    border: '#81d4fa',
                    highlight: {
                        background: '#3a3a3a',
                        border: '#81d4fa',
                    }
                },
                font: {color: '#c0c0c0', highlight: {color: '#fff'}},
                size: 10,
            });
            edges.push({from: ksId, to: tableId});
        });
    });

    const container = document.getElementById('topology-graph');
    const data = {
        nodes: new vis.DataSet(nodes),
        edges: new vis.DataSet(edges)
    };

    const options = {
        layout: {
            hierarchical: {
                direction: 'UD',
                sortMethod: 'directed',
                levelSeparation: 80,
                nodeSpacing: 150,
                blockShifting: true
            }
        },
        nodes: {
            font: {size: 14, color: '#333'},
            borderWidth: 2,
            shape: 'box',
            shapeProperties: {useBorderWithImage: true}
        },
        edges: {
            arrows: {to: true},
            smooth: true,
            color: '#e0e0e0'
        },
        physics: false
    };

    if (network) {
        network.destroy();
    }
    network = new vis.Network(container, data, options);
}
