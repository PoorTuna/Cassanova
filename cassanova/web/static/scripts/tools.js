const terminalForm = document.getElementById('terminal-form');
const terminalInput = document.getElementById('terminal-input');
const terminalOutput = document.getElementById('terminal-output');

let availableTools = [];

window.addEventListener('DOMContentLoaded', () => {
    fetch('/api/v1/tool/list')
        .then(res => res.json())
        .then(data => {
            availableTools = data.tools || [];
        })
        .catch(() => {
            printLine('Failed to fetch available tools.', '#ff5c5c');
        });
});

terminalForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const command = terminalInput.value.trim();
    if (!command) return;

    printLine(`cassanova@tools:~$ ${command}`, '#4fc3f7');
    terminalInput.value = '';

    if (command.toLowerCase() === 'help') {
        if (availableTools.length === 0) {
            printLine('No tools available. Try again later or check backend.', '#ff5c5c');
        } else {
            printLine('Available tools:\n' + availableTools.map(t => `- ${t}`).join('\n'));
        }
        return;
    }

    const parts = command.split(/\s+/);
    const tool = parts[0];
    const args = parts.slice(1).join(' ');

    const formData = new FormData();
    formData.append('tool', tool);
    if (args) formData.append('args', args);

    printLine('Running...', '#888');
    terminalInput.disabled = true;

    try {
        const res = await fetch('/api/v1/tool/run', {
            method: 'POST',
            body: formData
        });

        const json = await res.json();

        if (!res.ok) {
            const errorMsg = json.detail
                ? (Array.isArray(json.detail) ? json.detail.map(e => e.msg).join('; ') : json.detail)
                : json.error || JSON.stringify(json);
            printLine(`Error ${res.status}: ${errorMsg}`, '#ff5c5c');
        } else {
            printLine(json.stdout || '(no stdout)');
            if (json.stderr) {
                printLine(`\n[stderr]\n${json.stderr}`, '#ffa726');
            }
            printLine(`\n[exit code] ${json.exit_code}`, '#4fc3f7');
        }
    } catch (err) {
        printLine(`Network error: ${err.message}`, '#ff5c5c');
    }

    terminalInput.disabled = false;
    terminalInput.focus();
});

function printLine(text, color = '#c9d1d9') {
    text.split('\n').forEach(lineText => {
        const line = document.createElement('div');
        line.textContent = lineText;
        line.style.color = color;
        terminalOutput.appendChild(line);
    });
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}