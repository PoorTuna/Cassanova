window.originalClusterData = null;
window.network = null;

function getCSS(varName) {
    return getComputedStyle(document.body).getPropertyValue(varName).trim();
}

function renderTopologyGraph(cluster) {
    if (!cluster || !cluster.nodes) return;

    const nodes = [];
    const edges = [];

    const colorPrimary = getCSS('--color-primary') || '#D4AF37';
    const colorSecondary = getCSS('--color-secondary') || '#5FD6C4';
    const colorSuccess = getCSS('--color-success') || '#00E676';
    const bgSurface = getCSS('--bg-surface') || '#121212';
    const bgApp = getCSS('--bg-app') || '#0A0A0C';
    const textPrimary = getCSS('--text-primary') || '#F5F5F5';
    const textMuted = getCSS('--text-muted') || '#888888';

    const addedIds = new Set();
    const addNode = (n) => {
        if (!addedIds.has(n.id)) {
            nodes.push(n);
            addedIds.add(n.id);
        }
    };

    const clusterId = 'cluster';
    addNode({
        id: clusterId,
        label: cluster.metrics.name || 'Cluster',
        shape: 'hexagon',
        color: {
            background: colorPrimary + '33',
            border: colorPrimary,
        },
        font: { size: 24, color: colorPrimary, face: 'Outfit', strokeWidth: 0, bold: true },
        physics: false
    });

    const topology = {};
    cluster.nodes.forEach(node => {
        const dc = node.data_center || 'Default DC';
        const rack = node.rack || 'Default Rack';

        if (!topology[dc]) topology[dc] = {};
        if (!topology[dc][rack]) topology[dc][rack] = [];
        topology[dc][rack].push(node);
    });

    Object.keys(topology).forEach(dcName => {
        const dcId = `dc:${dcName}`;

        addNode({
            id: dcId,
            label: dcName,
            shape: 'box',
            color: { background: bgSurface, border: colorSecondary },
            font: { color: colorSecondary, size: 18, face: 'Outfit' },
            margin: 10,
            shadow: true
        });

        edges.push({ from: clusterId, to: dcId, width: 2, color: { color: colorPrimary, opacity: 0.4 } });

        Object.keys(topology[dcName]).forEach(rackName => {
            const rackId = `rack:${dcName}:${rackName}`;

            addNode({
                id: rackId,
                label: rackName,
                shape: 'ellipse',
                color: { background: bgApp, border: textMuted },
                font: { color: textMuted, size: 14 }
            });

            edges.push({ from: dcId, to: rackId, len: 100, color: { color: colorSecondary, opacity: 0.3 } });

            topology[dcName][rackName].forEach(node => {
                const nodeId = node.host_id;
                const displayIp = node.broadcast_address || node.rpc_address || node.listen_address || '0.0.0.0';

                addNode({
                    id: nodeId,
                    label: displayIp,
                    title: `Host ID: ${node.host_id}\nTokens: ${node.tokens ? node.tokens.length : 0}\nVer: ${node.release_version}`,
                    shape: 'dot',
                    size: 15,
                    color: {
                        background: colorSuccess,
                        border: textPrimary,
                        highlight: { background: colorSuccess, border: textPrimary }
                    },
                    font: { color: textPrimary, size: 12, strokeWidth: 2, strokeColor: bgApp }
                });

                edges.push({ from: rackId, to: nodeId, len: 80, color: { color: textMuted, opacity: 0.5 } });
            });
        });
    });

    const container = document.getElementById('topology-graph');
    if (!container) return;

    const navData = {
        nodes: new vis.DataSet(nodes),
        edges: new vis.DataSet(edges)
    };

    const options = {
        layout: {
            hierarchical: {
                enabled: true,
                direction: 'UD',
                sortMethod: 'directed',
                nodeSpacing: 150,
                levelSeparation: 150
            }
        },
        nodes: {
            borderWidth: 2,
            shadow: true
        },
        edges: {
            arrows: { to: false },
            smooth: { type: 'cubicBezier' },
            width: 1
        },
        physics: {
            enabled: false
        },
        interaction: {
            hover: true,
            tooltipDelay: 200,
            zoomView: true
        }
    };

    if (network) network.destroy();
    network = new vis.Network(container, navData, options);

    setTimeout(() => {
        network.fit({
            animation: {
                duration: 1000,
                easingFunction: 'easeInOutQuad'
            }
        });
    }, 500);
}
