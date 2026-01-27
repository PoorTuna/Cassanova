document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('schema-graph');

    if (!schemaData || !container) {
        console.warn("Required DOM elements for schema graph not found.");
        return;
    }

    renderSchemaGraph(container, schemaData);

    const filterInput = document.getElementById('table-filter');
    if (filterInput) {
        filterInput.addEventListener('input', () => {
            const filterVal = filterInput.value.toLowerCase();

            // Filter tables by name matching filterVal
            const filteredTables = schemaData.tables.filter(table =>
                table.name.toLowerCase().includes(filterVal)
            );

            // Clone original data and replace tables with filteredTables
            const filteredData = {
                ...schemaData,
                tables: filteredTables
            };

            renderSchemaGraph(container, filteredData);
        });
    }
});

function getCSS(varName) {
    return getComputedStyle(document.body).getPropertyValue(varName).trim();
}

function hexToRgba(hex, alpha) {
    if (!hex) return `rgba(100, 100, 100, ${alpha})`;
    let c;
    if (/^#([A-Fa-f0-9]{3}){1,2}$/.test(hex)) {
        c = hex.substring(1).split('');
        if (c.length == 3) {
            c = [c[0], c[0], c[1], c[1], c[2], c[2]];
        }
        c = '0x' + c.join('');
        return 'rgba(' + [(c >> 16) & 255, (c >> 8) & 255, c & 255].join(',') + ',' + alpha + ')';
    }
    return hex;
}

function renderSchemaGraph(container, keyspace) {
    const nodes = [];
    const edges = [];
    const addedIds = new Set();
    const addNode = (n) => { if (!addedIds.has(n.id)) { nodes.push(n); addedIds.add(n.id); } };
    const addEdge = (e) => edges.push(e);

    // Theme Colors (Dynamically fetched)
    const colorPrimary = getCSS('--color-primary') || '#D4AF37';
    const colorSecondary = getCSS('--color-secondary') || '#5FD6C4';
    const bgSurface = getCSS('--bg-surface') || '#121212';
    const bgPanel = getCSS('--bg-panel') || '#1e1e1e';
    const textPrimary = getCSS('--text-primary') || '#F5F5F5';
    const textMuted = getCSS('--text-muted') || '#888888';

    // Glassy Colors derived from Theme
    const glassBorder = hexToRgba(colorPrimary, 0.3);
    const nodeBorder = hexToRgba(colorSecondary, 0.5);
    const nodeBackground = hexToRgba(bgPanel, 0.8);

    // Root Node (Central Hub) - RESTORED & THEMED
    const rootId = 'root';
    addNode({
        id: rootId,
        label: keyspace.name,
        shape: 'dot',
        size: 25,
        color: {
            background: hexToRgba(colorPrimary, 0.2),
            border: colorPrimary,
            highlight: { background: colorPrimary, border: textPrimary }
        },
        font: {
            size: 22,
            color: textPrimary,
            face: 'Outfit',
            bold: true,
            strokeWidth: 4,
            strokeColor: bgSurface
        },
        margin: 15,
        shadow: { enabled: true, color: 'rgba(0,0,0,0.5)', size: 10, x: 5, y: 5 }
    });

    // Helper for groups
    const createGroup = (items, typeLabel) => {
        if (!items || items.length === 0) return;

        items.forEach(item => {
            const name = item.name || 'Unknown';
            const itemId = `${typeLabel}:${name}`;
            const colCount = item.columns ? Object.keys(item.columns).length : 0;

            // Revert to plain text label to avoid raw HTML issues
            // Showing simplified info to reduce clutter
            const isTable = typeLabel === 'table';
            const labelText = isTable ? `${name}\n(${colCount} cols)` : name;

            addNode({
                id: itemId,
                label: labelText,
                shape: 'box',
                margin: 12,
                color: {
                    background: nodeBackground,
                    border: isTable ? nodeBorder : glassBorder,
                    highlight: {
                        background: hexToRgba(colorSecondary, 0.2),
                        border: colorSecondary
                    }
                },
                font: {
                    multi: false, // Standard text rendering
                    color: textPrimary,
                    size: 14,
                    face: 'Inter, sans-serif',
                    vadjust: 0
                },
                shadow: { enabled: true, color: 'rgba(0,0,0,0.3)', size: 5, x: 3, y: 3 },
                title: 'Click to view details',
                shapeProperties: { borderRadius: 8 }
            });

            addEdge({
                from: rootId,
                to: itemId,
                color: { color: glassBorder, opacity: 0.3 },
                width: 1
            });
        });
    };

    // 1. Tables
    createGroup(keyspace.tables, 'table');

    // 2. UDTs
    if (keyspace.user_types) {
        Object.keys(keyspace.user_types).forEach(udt => {
            addNode({
                id: `udt:${udt}`,
                label: `${udt}\n(UDT)`,
                shape: 'ellipse',
                color: { background: hexToRgba(colorPrimary, 0.1), border: hexToRgba(colorPrimary, 0.4) },
                font: { color: textMuted, size: 12 },
                shadow: true
            });
            addEdge({ from: rootId, to: `udt:${udt}`, color: { color: glassBorder, opacity: 0.2 } });
        });
    }

    const data = {
        nodes: new vis.DataSet(nodes),
        edges: new vis.DataSet(edges)
    };

    // Physics / Layout Configuration
    // Switched to Hierarchical (Top-Down) as requested to match Topology graph
    const options = {
        layout: {
            hierarchical: {
                enabled: true,
                direction: 'UD',        // Up-Down layout
                sortMethod: 'directed', // Respect edge direction (Root -> Tables)
                levelSeparation: 300,   // Vertical spacing between Keyspace and Tables
                nodeSpacing: 300,       // Horizontal spacing between tables to prevent overlap
                treeSpacing: 300,
                blockShifting: true,
                edgeMinimization: true,
                parentCentralization: true,
                shakeTowards: 'roots'
            }
        },
        nodes: {
            borderWidth: 1,
            widthConstraint: { maximum: 250 }
        },
        edges: {
            arrows: { to: true }, // Arrows make more sense in a hierarchy
            color: { color: glassBorder },
            smooth: {
                type: 'cubicBezier',
                forceDirection: 'vertical',
                roundness: 0.4
            }
        },
        physics: {
            enabled: false // Static layout prevents "cramming" & jitter
        },
        interaction: {
            hover: true,
            zoomView: true,
            dragView: true,
            navigationButtons: false, // Removed controls
            keyboard: true
        }
    };

    if (window.schemaNetwork) window.schemaNetwork.destroy();
    window.schemaNetwork = new vis.Network(container, data, options);

    // Initial Zoom (Start zoomed in)
    // Wait for stabilization or first render
    window.schemaNetwork.once("afterDrawing", function () {
        window.schemaNetwork.moveTo({
            scale: 1.2, // Zoom in (1.0 is default fit, >1.0 is closer)
            animation: {
                duration: 1000,
                easingFunction: 'easeInOutQuad'
            }
        });
    });

    // Interaction: Click to scroll to definition
    window.schemaNetwork.on("click", function (params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            if (nodeId.startsWith('table:')) {
                const tableName = nodeId.split(':')[1];

                const filterInput = document.getElementById('table-filter');
                if (filterInput) {
                    filterInput.value = tableName;
                    filterInput.dispatchEvent(new Event('input'));
                }

                const listEl = document.getElementById('table-list');
                if (listEl) listEl.scrollIntoView({ behavior: 'smooth' });
            }
        }
    });
}
