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
                <span class="trace-duration">${(event.duration * 1000).toFixed(2)} ms</span>
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
                <strong>Total Duration:</strong> <span style="color: var(--color-warning); font-weight: 700;">${trace.duration} ms</span>
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