document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('schema-graph');

    if (!schemaData || !container) {
        console.warn("Required DOM elements for schema graph not found.");
        return;
    }
    
    renderSchemaGraph(container, schemaData);

    // Optional: keep filter but only filter tables, columns always shown under visible tables
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

function createRootNode(keyspaceName) {
    return {
        id: `keyspace-${keyspaceName}`,
        label: keyspaceName,
        shape: 'box',
        color: {background: '#121212', border: '#81d4fa'},
        font: {color: '#fff', size: 16}
    };
}

function createGroupLabelNode(groupId, groupLabel) {
    return {
        id: `${groupId}-label`,
        label: groupLabel,
        shape: 'box',
        color: {background: '#333', border: '#888'},
        font: {color: '#eee', size: 14},
        widthConstraint: {maximum: 140}
    };
}

function addGroupNodes(nodes, edges, items, groupId, groupLabel, shape, color, rootId) {
    if (!items || Object.keys(items).length === 0) return;

    const labelNode = createGroupLabelNode(groupId, groupLabel);
    nodes.push(labelNode);
    edges.push({from: rootId, to: labelNode.id});

    Object.entries(items).forEach(([name, item]) => {
        const nodeId = `${groupId}-${name}`;
        nodes.push({
            id: nodeId,
            label: name,
            shape,
            color,
            font: {color: '#eee'}
        });
        edges.push({from: labelNode.id, to: nodeId});

        // If this group is 'tables', add columns as children nodes
        if (groupId === 'table' && item.columns) {
            Object.entries(item.columns).forEach(([colName]) => {
                const colNodeId = `${nodeId}-col-${colName}`;
                nodes.push({
                    id: colNodeId,
                    label: colName,
                    shape: 'ellipse',
                    color: {background: '#555', border: '#999'},
                    font: {color: '#ccc', size: 12}
                });
                edges.push({from: nodeId, to: colNodeId});
            });
        }
    });
}

function renderSchemaGraph(container, keyspace) {
    const nodes = [];
    const edges = [];

    const rootNode = createRootNode(keyspace.name);
    nodes.push(rootNode);

    addGroupNodes(
        nodes,
        edges,
        keyspace.tables.reduce((acc, t) => {
            acc[t.name] = t;
            return acc;
        }, {}),
        'table',
        'Tables',
        'box',
        {background: '#1e1e1e', border: '#4fc3f7'},
        rootNode.id
    );

    addGroupNodes(nodes, edges, keyspace.user_types, 'udt', 'User Types', 'diamond', {
        background: '#2a2a40',
        border: '#7c4dff'
    }, rootNode.id);

    addGroupNodes(nodes, edges, keyspace.views, 'view', 'Views', 'box', {
        background: '#4a148c',
        border: '#ce93d8'
    }, rootNode.id);

    addGroupNodes(nodes, edges, keyspace.functions, 'func', 'Functions', 'ellipse', {
        background: '#004d40',
        border: '#26a69a'
    }, rootNode.id);

    addGroupNodes(nodes, edges, keyspace.aggregates, 'agg', 'Aggregates', 'hexagon', {
        background: '#263238',
        border: '#4fc3f7'
    }, rootNode.id);

    const data = {
        nodes: new vis.DataSet(nodes),
        edges: new vis.DataSet(edges)
    };

    const options = {
        layout: {
            hierarchical: {
                direction: 'UD',
                sortMethod: 'directed',
                levelSeparation: 100,
                nodeSpacing: 120
            }
        },
        nodes: {
            font: {size: 14},
            borderWidth: 2,
            widthConstraint: {maximum: 140}
        },
        edges: {
            arrows: {to: true},
            color: '#aaa',
            smooth: true
        },
        physics: false
    };

    new vis.Network(container, data, options);
}
