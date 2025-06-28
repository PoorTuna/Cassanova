const form = document.getElementById('tools-form');
const drawer = document.getElementById('tools-result-drawer');
const closeDrawerBtn = document.getElementById('close-tools-drawer-btn');
const stdoutPre = document.getElementById('stdout');
const stderrPre = document.getElementById('stderr');
const exitCodePre = document.getElementById('exit-code');
const spinner = document.getElementById('spinner');
const downloadBtn = document.getElementById('download-output-btn');
const tabs = document.querySelectorAll('.output-tabs .tab');

const toolSelect = document.getElementById('tool-select');
const argsInput = document.getElementById('args-input');

// Load saved inputs on page load
window.addEventListener('DOMContentLoaded', () => {
    const savedTool = localStorage.getItem('lastTool');
    const savedArgs = localStorage.getItem('lastArgs');

    if (savedTool) toolSelect.value = savedTool;
    if (savedArgs) argsInput.value = savedArgs;
});

// Tab switching logic
tabs.forEach(tab => {
    tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        const target = tab.dataset.target;
        stdoutPre.style.display = target === 'stdout' ? 'block' : 'none';
        stderrPre.style.display = target === 'stderr' ? 'block' : 'none';
        exitCodePre.style.display = target === 'exit-code' ? 'block' : 'none';
    });
});

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Save current inputs
    localStorage.setItem('lastTool', toolSelect.value);
    localStorage.setItem('lastArgs', argsInput.value);

    // Clear output & show spinner & open drawer immediately
    stdoutPre.textContent = '';
    stderrPre.textContent = '';
    exitCodePre.textContent = '';
    drawer.classList.add('open');
    spinner.style.display = 'inline-block';

    const formData = new FormData(form);

    try {
        const resp = await fetch('/api/v1/tool/run', {
            method: 'POST',
            body: formData,
        });

        spinner.style.display = 'none';

        const json = await resp.json();

        if (!resp.ok) {
            const errorMsg = json.detail
                ? (Array.isArray(json.detail)
                    ? json.detail.map(e => e.msg).join('; ')
                    : json.detail)
                : json.error || JSON.stringify(json);
            alert(`Error ${resp.status}: ${errorMsg}`);
            return;
        }

        stdoutPre.textContent = json.stdout || '(no output)';
        stderrPre.textContent = json.stderr || '(no error)';
        exitCodePre.textContent = json.exit_code ?? '(unknown)';
    } catch (err) {
        spinner.style.display = 'none';
        alert(`Network error: ${err.message}`);
    }
});
closeDrawerBtn.addEventListener('click', () => {
    drawer.classList.remove('open');
});

// Download output as JSON
downloadBtn.addEventListener('click', () => {
    const data = {
        stdout: stdoutPre.textContent,
        stderr: stderrPre.textContent,
        exit_code: exitCodePre.textContent,
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `tool_output_${Date.now()}.json`;
    a.click();

    URL.revokeObjectURL(url);
});