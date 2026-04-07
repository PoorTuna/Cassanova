require.config({ paths: { vs: '/static/scripts/vendor/monaco' } });
window.editorInstance = null;
let clusterSchema = null;

const CQL_KEYWORDS = [
    'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'FROM', 'INTO', 'WHERE',
    'SET', 'VALUES', 'AND', 'OR', 'LIMIT', 'ALLOW FILTERING', 'ORDER BY', 'ASC', 'DESC',
    'CREATE', 'KEYSPACE', 'TABLE', 'INDEX', 'DROP', 'PRIMARY KEY', 'IF NOT EXISTS',
    'BEGIN', 'BATCH', 'APPLY', 'USING', 'TTL', 'TIMESTAMP', 'WRITETIME', 'JSON', 'DISTINCT'
];

const _SCHEMA_CACHE_KEY = `cassanova_schema_${clusterName}`;
const _SCHEMA_CACHE_TS_KEY = `cassanova_schema_ts_${clusterName}`;
const _SCHEMA_CACHE_TTL_MS = 60000;

function loadCachedSchema() {
    try {
        const cached = sessionStorage.getItem(_SCHEMA_CACHE_KEY);
        const ts = parseInt(sessionStorage.getItem(_SCHEMA_CACHE_TS_KEY) || '0', 10);
        if (cached && (Date.now() - ts) < _SCHEMA_CACHE_TTL_MS) {
            clusterSchema = JSON.parse(cached);
            console.log("Cassanova: Schema loaded from cache");
            return true;
        }
    } catch (e) { /* ignore parse errors */ }
    return false;
}

async function fetchSchema() {
    try {
        const response = await fetch(`/api/v1/cluster/${encodeURIComponent(clusterName)}/schema-map`);
        if (response.ok) {
            clusterSchema = await response.json();
            try {
                sessionStorage.setItem(_SCHEMA_CACHE_KEY, JSON.stringify(clusterSchema));
                sessionStorage.setItem(_SCHEMA_CACHE_TS_KEY, String(Date.now()));
            } catch (e) { /* sessionStorage full or unavailable */ }
            console.log("Cassanova: Schema Map Loaded for IntelliSense");
        }
    } catch (e) {
        console.error("Cassanova: Failed to fetch schema:", e);
    }
}

// Start schema fetch immediately — don't wait for Monaco to load
loadCachedSchema();
fetchSchema();

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

    const savedContent = localStorage.getItem(`cqlsh_editor_${clusterName}`);
    const defaultContent = "-- Write your CQL queries here\n-- Ctrl+Enter runs the statement at cursor\n-- Select multiple statements to run them all\nSELECT * FROM system_schema.keyspaces;";

    window.editorInstance = monaco.editor.create(document.getElementById('monaco-editor'), {
        value: savedContent || defaultContent,
        language: 'sql',
        theme: 'vs-dark',
        automaticLayout: false,
        minimap: { enabled: false },
        fontSize: 14,
        tabSize: 2,
        lineNumbers: 'on',
        padding: { top: 16 },
    });

    // Persist editor content on change (debounced)
    let _saveTimer;
    window.editorInstance.onDidChangeModelContent(() => {
        clearTimeout(_saveTimer);
        _saveTimer = setTimeout(() => {
            localStorage.setItem(`cqlsh_editor_${clusterName}`, window.editorInstance.getValue());
        }, 500);
    });

    // Ctrl+Enter keybinding
    window.editorInstance.addCommand(
        monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter,
        () => { if (window.runQuery) window.runQuery(); }
    );

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
                <span class="trace-desc">${escapeHtml(event.description)}</span>
                <span class="trace-duration">${event.elapsed_ms.toFixed(3)} ms</span>
            </div>
            <div class="trace-source">Source: ${escapeHtml(event.source)}</div>
        </div>
    `).join('');

    traceEl.innerHTML = `
        <div class="trace-summary" style="margin-bottom: 20px; padding: 15px; background: rgba(var(--color-primary-rgb), 0.1); border-radius: 8px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <strong>Coordinator:</strong> <span>${escapeHtml(trace.coordinator)}</span>
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

function getStatementAtCursor() {
    const editor = window.editorInstance;
    const text = editor.getValue();
    const offset = editor.getModel().getOffsetAt(editor.getPosition());
    const parts = text.split(';');
    let pos = 0;
    for (const part of parts) {
        const start = pos;
        const end = pos + part.length;
        if (offset >= start && offset <= end) {
            return part.trim();
        }
        pos = end + 1;
    }
    return text.trim();
}

async function executeStatement(cql, consistency, tracing) {
    const res = await fetch(`/api/v1/cluster/${encodeURIComponent(clusterName)}/operations/cqlsh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cql, cl: consistency, enable_tracing: tracing }),
    });
    if (!res.ok) {
        let errorText = await res.text();
        try {
            const errorJson = JSON.parse(errorText);
            errorText = errorJson.detail || JSON.stringify(errorJson);
        } catch { }
        throw new Error(errorText || res.statusText);
    }
    return res.json();
}

window.runQuery = async function runQuery() {
    if (!window.editorInstance) return;

    const selection = window.editorInstance.getSelection();
    const model = window.editorInstance.getModel();
    const selectedText = selection && !selection.isEmpty() ? model.getValueInRange(selection).trim() : '';

    const rawCql = selectedText || getStatementAtCursor();
    const statements = rawCql.split(';').map(s => s.trim()).filter(Boolean);

    if (!statements.length) {
        resultEl.textContent = 'No statement to run.';
        return;
    }

    const consistencyString = consistencySelect ? consistencySelect.value : 'QUORUM';
    const consistency = consistencyMap[consistencyString] ?? 4;
    const tracingCheckbox = document.getElementById('enable-tracing');
    const tracing = tracingCheckbox ? tracingCheckbox.checked : false;

    runBtn.disabled = true;
    resultEl.innerHTML = '<span class="loading">Running...</span>';
    document.getElementById('trace-result').innerHTML = '';
    tabBtns[0].click();

    const allResults = [];
    let lastTrace = null;

    try {
        for (const stmt of statements) {
            const data = await executeStatement(stmt, consistency, tracing);

            if (!queryHistory.includes(stmt)) {
                queryHistory.unshift(stmt);
                if (queryHistory.length > 30) queryHistory.pop();
            }

            const actualData = data.result || data;
            allResults.push(actualData.result || actualData);

            const traceData = data.trace || (actualData && actualData.trace);
            if (traceData) lastTrace = traceData;
        }

        localStorage.setItem('cqlshHistory', JSON.stringify(queryHistory));
        updateHistoryUI();

        const combined = statements.length === 1 ? allResults[0] : allResults;
        try {
            if (window.syntaxHighlight) {
                resultEl.innerHTML = window.syntaxHighlight(combined);
            } else {
                resultEl.textContent = JSON.stringify(combined, null, 2);
            }
        } catch (e) {
            resultEl.textContent = JSON.stringify(combined, null, 2);
        }

        if (lastTrace) {
            renderTrace(lastTrace);
        } else {
            document.getElementById('trace-result').innerHTML = '<em>Tracing was not enabled.</em>';
        }
    } catch (err) {
        resultEl.innerHTML = `<span class="error">Error: ${escapeHtml(err.toString())}</span>`;
    } finally {
        runBtn.disabled = false;
    }
};

runBtn.addEventListener('click', window.runQuery);

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

// Register for auto-refresh widget — refreshes schema for autocomplete
window.cassanovaRefresh = () => fetchSchema();