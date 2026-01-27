require.config({ paths: { vs: '/static/scripts/vendor/monaco' } });
window.editorInstance = null;
let clusterSchema = null;

const CQL_KEYWORDS = [
    'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'FROM', 'INTO', 'WHERE',
    'SET', 'VALUES', 'AND', 'OR', 'LIMIT', 'ALLOW FILTERING', 'ORDER BY', 'ASC', 'DESC',
    'CREATE', 'KEYSPACE', 'TABLE', 'INDEX', 'DROP', 'PRIMARY KEY', 'IF NOT EXISTS',
    'BEGIN', 'BATCH', 'APPLY', 'USING', 'TTL', 'TIMESTAMP', 'WRITETIME', 'JSON', 'DISTINCT'
];

async function fetchSchema() {
    try {
        const response = await fetch(`/api/v1/cluster/${encodeURIComponent(clusterName)}/schema-map`);
        if (response.ok) {
            clusterSchema = await response.json();
            console.log("Cassanova: Schema Map Loaded for IntelliSense");
        }
    } catch (e) {
        console.error("Cassanova: Failed to fetch schema:", e);
    }
}

require(['vs/editor/editor.main'], function () {
    // Basic context parser to see what we should suggest
    function getContext(model, position) {
        const line = model.getLineContent(position.lineNumber);
        const textBefore = line.substring(0, position.column - 1).toUpperCase();
        const words = textBefore.split(/\s+/).filter(x => x);
        const lastWord = words[words.length - 1] || "";

        if (lastWord === "FROM" || lastWord === "INTO" || lastWord === "TABLE" || lastWord === "UPDATE") {
            return "SOURCE";
        }

        // Handle dotted path: keyspace.table or keyspace.
        if (lastWord.includes('.')) {
            const parts = lastWord.split('.');
            const ks = parts[0].toLowerCase();
            if (clusterSchema && clusterSchema[ks]) {
                return { type: "TABLE_IN_KS", ks: ks };
            }
        }

        // Only suggest keywords if at start of line or after whitespace
        if (words.length === 0 || words.length === 1 && !line.includes(' ')) {
            return "GENERAL";
        }

        const fullText = model.getValue().toUpperCase();
        const fromMatch = fullText.match(/FROM\s+([a-zA-Z0-9_.]+)/);
        if (fromMatch) {
            const source = fromMatch[1].split('.');
            let ks = null;
            let tb = null;
            if (source.length === 2) { [ks, tb] = source; } else { tb = source[0]; }
            return { type: "COLUMN", ks: ks?.toLowerCase(), tb: tb.toLowerCase() };
        }

        return "GENERAL";
    }

    monaco.languages.registerCompletionItemProvider('sql', {
        triggerCharacters: ['.'],
        provideCompletionItems: (model, position) => {
            const word = model.getWordUntilPosition(position);
            const range = {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: word.startColumn,
                endColumn: word.endColumn
            };

            const suggestions = [];
            const context = getContext(model, position);

            function maybeQuote(name) {
                if (name !== name.toLowerCase() || /[^a-z0-9_]/.test(name)) {
                    return `"${name}"`;
                }
                return name;
            }

            // 1. Suggest Keywords
            if (context === "GENERAL") {
                CQL_KEYWORDS.forEach(k => {
                    suggestions.push({
                        label: k,
                        kind: monaco.languages.CompletionItemKind.Keyword,
                        insertText: k,
                        range: range
                    });
                });
            }

            if (!clusterSchema) return { suggestions: suggestions };

            // 2. Suggest Keyspaces
            if (context === "SOURCE" || context === "GENERAL") {
                Object.keys(clusterSchema).forEach(ks => {
                    const quoted = maybeQuote(ks);
                    suggestions.push({
                        label: quoted,
                        kind: monaco.languages.CompletionItemKind.Module,
                        insertText: quoted,
                        detail: 'Keyspace',
                        range: range
                    });
                });
            }

            // 3. Suggest Tables
            if (context.type === "TABLE_IN_KS") {
                const tables = clusterSchema[context.ks];
                if (tables) {
                    Object.keys(tables).forEach(tb => {
                        const quoted = maybeQuote(tb);
                        suggestions.push({
                            label: quoted,
                            kind: monaco.languages.CompletionItemKind.Class,
                            insertText: quoted,
                            detail: `Table in ${context.ks}`,
                            range: range
                        });
                    });
                }
            } else if (context.type === "COLUMN") {
                let columns = [];
                if (context.ks) {
                    columns = clusterSchema[context.ks]?.[context.tb] || [];
                } else {
                    for (const ks in clusterSchema) {
                        if (clusterSchema[ks][context.tb]) {
                            columns = clusterSchema[ks][context.tb];
                            break;
                        }
                    }
                }
                columns.forEach(col => {
                    const quoted = maybeQuote(col);
                    suggestions.push({
                        label: quoted,
                        kind: monaco.languages.CompletionItemKind.Field,
                        insertText: quoted,
                        detail: `Column in ${context.tb}`,
                        range: range
                    });
                });
            }

            return { suggestions: suggestions };
        }
    });

    window.editorInstance = monaco.editor.create(document.getElementById('monaco-editor'), {
        value: "-- Write your CQL query here\n-- Use mouse selection if there are multiple queries\nSELECT * FROM system_schema.keyspaces;",
        language: 'sql',
        theme: 'vs-dark',
        automaticLayout: false,
        minimap: { enabled: false },
        fontSize: 14,
        tabSize: 2,
        lineNumbers: 'on',
        padding: { top: 16 },
    });

    fetchSchema();
});

const container = document.getElementById('container');
const editor = document.getElementById('editor');
const resizer = document.getElementById('resizer');
const runBtn = document.getElementById('run-btn');
const resultEl = document.getElementById('query-result');
const consistencySelect = document.getElementById('consistency-level');
const consistencyMap = {
    ANY: 0,
    ONE: 1,
    TWO: 2,
    THREE: 3,
    QUORUM: 4,
    ALL: 5,
    LOCAL_QUORUM: 6,
    EACH_QUORUM: 7,
    SERIAL: 8,
    LOCAL_SERIAL: 9,
    LOCAL_ONE: 10,
};
const historyList = document.getElementById('history-list');
let queryHistory = [];

let isResizing = false;

resizer.addEventListener('mousedown', () => {
    isResizing = true;
    document.body.style.cursor = 'col-resize';
});

document.addEventListener('mouseup', () => {
    if (isResizing) {
        isResizing = false;
        document.body.style.cursor = 'default';
    }
});

document.addEventListener('mousemove', (e) => {
    if (!isResizing) return;

    const containerRect = container.getBoundingClientRect();
    let newWidth = e.clientX - containerRect.left;

    const minWidth = containerRect.width * 0.2;
    const maxWidth = containerRect.width * 0.8;

    if (newWidth < minWidth) newWidth = minWidth;
    if (newWidth > maxWidth) newWidth = maxWidth;

    editor.style.flexBasis = newWidth + 'px';

    if (window.editorInstance) {
        window.requestAnimationFrame(() => {
            window.editorInstance.layout();
        });
    }
});

const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const target = btn.dataset.tab;
        tabBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(target).classList.add('active');
    });
});

function renderTrace(trace) {
    const traceEl = document.getElementById('trace-result');
    if (!trace) {
        traceEl.innerHTML = '<em>No trace info available.</em>';
        return;
    }

    const eventsHtml = trace.events.map(event => `
        <div class="trace-item">
            <div class="trace-header">
                <span class="trace-desc">${event.description}</span>
                <span class="trace-duration">${event.elapsed_ms.toFixed(3)} ms</span>
            </div>
            <div class="trace-source">Source: ${event.source}</div>
        </div>
    `).join('');

    traceEl.innerHTML = `
        <div class="trace-summary" style="margin-bottom: 20px; padding: 15px; background: rgba(var(--color-primary-rgb), 0.1); border-radius: 8px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <strong>Coordinator:</strong> <span>${trace.coordinator}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <strong>Total Duration:</strong> <span style="color: var(--color-warning); font-weight: 700;">${trace.duration_ms.toFixed(3)} ms</span>
            </div>
        </div>
        <div class="trace-container">
            ${eventsHtml}
        </div>
    `;
}

runBtn.addEventListener('click', () => {
    if (!window.editorInstance) return;

    const selection = window.editorInstance.getSelection();
    const model = window.editorInstance.getModel();

    let cql = '';

    if (selection && !selection.isEmpty()) {
        cql = model.getValueInRange(selection);
    } else {
        cql = window.editorInstance.getValue();
    }

    cql = cql.trim();

    if (!cql) {
        resultEl.textContent = 'Please enter a CQL query.';
        return;
    }

    const consistencyString = consistencySelect ? consistencySelect.value : 'QUORUM';
    const consistency = consistencyMap[consistencyString] ?? 4;
    const tracingCheckbox = document.getElementById('enable-tracing');
    const tracing = tracingCheckbox ? tracingCheckbox.checked : false;

    runBtn.disabled = true;
    resultEl.innerHTML = '<span class="loading">Running query...</span>';
    document.getElementById('trace-result').innerHTML = '<em>Waiting for trace...</em>';

    // Switch to results tab on new run
    tabBtns[0].click();

    fetch(`/api/v1/cluster/${encodeURIComponent(clusterName)}/operations/cqlsh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cql: cql, cl: consistency, enable_tracing: tracing }),
    })
        .then(async (res) => {
            runBtn.disabled = false;
            if (!res.ok) {
                let errorText = await res.text();
                try {
                    const errorJson = JSON.parse(errorText);
                    errorText = errorJson.detail || JSON.stringify(errorJson);
                } catch { }
                throw new Error(errorText || res.statusText);
            }
            return res.json();
        })
        .then((data) => {
            if (!queryHistory.includes(cql)) {
                queryHistory.unshift(cql);
                if (queryHistory.length > 30) queryHistory.pop();
                localStorage.setItem('cqlshHistory', JSON.stringify(queryHistory));
                updateHistoryUI();
            }

            const actualData = data.result || data;
            const traceData = data.trace || (data.result && data.result.trace);

            try {
                if (window.syntaxHighlight) {
                    resultEl.innerHTML = window.syntaxHighlight(actualData.result || actualData);
                } else {
                    resultEl.textContent = JSON.stringify(actualData, null, 2);
                }
            } catch (e) {
                resultEl.textContent = JSON.stringify(actualData, null, 2);
            }

            if (traceData) {
                renderTrace(traceData);
                // Optionally auto-switch to trace if it's a long execution or requested
                // For now, just show a badge on the tab if possible
            } else {
                document.getElementById('trace-result').innerHTML = '<em>No trace info available (Tracing was not enabled for this run).</em>';
            }
        })
        .catch((err) => {
            resultEl.innerHTML = `<span class="error">Error: ${err.toString()}</span>`;
        });
});

function updateHistoryUI() {
    historyList.innerHTML = '';
    queryHistory.forEach((cql, idx) => {
        const entry = document.createElement('li');
        entry.textContent = cql.slice(0, 100);
        entry.title = cql;
        entry.onclick = () => {
            window.editorInstance.setValue(cql);
        };
        historyList.appendChild(entry);
    });
}

document.getElementById('export-btn').addEventListener('click', () => {
    const content = resultEl.textContent;
    if (!content) return;

    const blob = new Blob([content], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = `cql_result_${Date.now()}.json`;
    link.click();

    URL.revokeObjectURL(url);
});
document.getElementById('clear-history-btn').addEventListener('click', () => {
    localStorage.removeItem('cqlshHistory');
    historyList.innerHTML = '';
    queryHistory = [];
});
window.addEventListener('DOMContentLoaded', () => {
    const saved = localStorage.getItem('cqlshHistory');
    if (saved) {
        try {
            queryHistory = JSON.parse(saved);
            queryHistory.forEach((cql) => {
                const entry = document.createElement('li');
                entry.textContent = cql.slice(0, 100);
                entry.title = cql;
                entry.onclick = () => {
                    window.editorInstance.setValue(cql);
                };
                historyList.appendChild(entry);
            });
        } catch {
            console.warn('Invalid saved CQL history');
        }
    }
});

const toggleBtn = document.getElementById('toggle-history-btn');
const historyDrawer = document.getElementById('history-drawer');
const closeBtn = document.getElementById('close-history-btn'); // new close button

function closeDrawer() {
    historyDrawer.classList.remove('open');
    toggleBtn.textContent = 'Show History';
}

if (toggleBtn && historyDrawer) {
    toggleBtn.addEventListener('click', (e) => {
        e.stopPropagation(); // prevent outside-click from firing
        const isOpen = historyDrawer.classList.contains('open');
        historyDrawer.classList.toggle('open');
        toggleBtn.textContent = isOpen ? 'Show History' : 'Hide History';
    });
}

if (closeBtn) {
    closeBtn.addEventListener('click', closeDrawer);
}

// Auto-close if clicking outside the drawer or toggle button
document.addEventListener('click', (e) => {
    if (
        historyDrawer.classList.contains('open') &&
        !historyDrawer.contains(e.target) &&
        !toggleBtn.contains(e.target)
    ) {
        closeDrawer();
    }
});