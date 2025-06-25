require.config({paths: {vs: 'https://unpkg.com/monaco-editor@latest/min/vs'}});

window.editorInstance = null;

require(['vs/editor/editor.main'], function () {
    window.editorInstance = monaco.editor.create(document.getElementById('monaco-editor'), {
        value: "-- Write your CQL query here\n-- Use mouse selection if there are multiple queries\nSELECT * FROM system_schema.keyspaces;",
        language: 'sql', // closest for CQL
        theme: 'vs-dark',
        automaticLayout: false, // manual layout control for better resizing
        minimap: {enabled: false},
        fontSize: 14,
        tabSize: 2,
        lineNumbers: 'on',
    });
});

const container = document.getElementById('container');
const editor = document.getElementById('editor');
const resizer = document.getElementById('resizer');
const runBtn = document.getElementById('run-btn');
const resultEl = document.getElementById('result');
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
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({cql: cql, cl: consistency, enable_tracing: tracing}),
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
            try {
                resultEl.textContent = JSON.stringify(data, null, 2);
            } catch {
                resultEl.textContent = data;
            }
        })
        .catch((err) => {
            resultEl.innerHTML = `<span class="error">Error: ${err.toString()}</span>`;
        });

});
