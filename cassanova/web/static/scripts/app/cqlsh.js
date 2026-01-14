require.config({ paths: { vs: '/static/scripts/vendor/monaco' } });

window.editorInstance = null;

require(['vs/editor/editor.main'], function () {
    window.editorInstance = monaco.editor.create(document.getElementById('monaco-editor'), {
        value: "-- Write your CQL query here\n-- Use mouse selection if there are multiple queries\nSELECT * FROM system_schema.keyspaces;",
        language: 'sql', // closest for CQL
        theme: 'vs-dark',
        automaticLayout: false, // manual layout control for better resizing
        minimap: { enabled: false },
        fontSize: 14,
        tabSize: 2,
        lineNumbers: 'on',
    });
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
                } catch {
                    // ignore JSON parse error
                }
                if (typeof errorText !== 'string') {
                    errorText = JSON.stringify(errorText);
                }
                throw new Error(errorText || res.statusText);
            }
            return res.json();
        })
        .then((data) => {
            if (!queryHistory.includes(cql)) {
                queryHistory.unshift(cql);
                if (queryHistory.length > 30) queryHistory.pop(); // max 30 entries
                localStorage.setItem('cqlshHistory', JSON.stringify(queryHistory));

                const entry = document.createElement('li');
                entry.textContent = cql.slice(0, 100);
                entry.title = cql;
                entry.onclick = () => {
                    window.editorInstance.setValue(cql);
                };
                historyList.prepend(entry);
                if (historyList.children.length > 30) {
                    historyList.removeChild(historyList.lastChild);
                }
            }

            try {
                if (window.syntaxHighlight) {
                    resultEl.innerHTML = window.syntaxHighlight(data);
                } else {
                    // Fallback formatting if library missing
                    resultEl.textContent = JSON.stringify(data, null, 2);
                }
            } catch (e) {
                console.error("Highlighting failed:", e);
                resultEl.textContent = JSON.stringify(data, null, 2);
            }
        })
        .catch((err) => {
            resultEl.innerHTML = `<span class="error">Error: ${err.toString()}</span>`;
        });

});

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