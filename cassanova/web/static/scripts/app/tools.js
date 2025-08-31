import { Terminal } from '/static/scripts/vendor/xterm/xterm-esm.js';
import { FitAddon } from '/static/scripts/vendor/xterm/xterm-addon-fit-esm.js';

const PROMPT = 'cassanova@tools:~$ ';
const term = new Terminal({
    fontFamily: "'Fira Mono', monospace",
    fontSize: 18,
    theme: {
        background: '#0d1117',
        foreground: '#c9d1d9',
        cursor: '#4fc3f7',
    },
    cursorBlink: true
});

const fitAddon = new FitAddon();
term.loadAddon(fitAddon);
term.open(document.getElementById('xterm-container'));
fitAddon.fit();

let commandBuffer = '';
let cursorPos = 0;
let history = [];
let historyIndex = -1;
let lastCommandOutput = '';

term.writeln('Welcome to Cassanova Tools Terminal');
printPrompt();

term.onKey(({ key, domEvent }) => {
    const printable = !domEvent.altKey && !domEvent.ctrlKey && !domEvent.metaKey;

    if (domEvent.key.toLowerCase() === 'l' && domEvent.ctrlKey) {
        term.clear();
        printPrompt();
        redrawInput();
        return;
    }

    if (domEvent.key.toLowerCase() === 's' && domEvent.ctrlKey) {
        exportLastResult();
        return;
    }

    if (domEvent.key === 'F5') {
        domEvent.preventDefault();
        window.location.reload();
        return;
    }

    switch (domEvent.key) {
        case 'Enter':
            term.write('\r\n');
            handleCommand(commandBuffer.trim());
            if (commandBuffer.trim()) history.push(commandBuffer);
            historyIndex = history.length;
            commandBuffer = '';
            cursorPos = 0;
            break;
        case 'Backspace':
            if (cursorPos > 0) {
                commandBuffer = commandBuffer.slice(0, cursorPos - 1) + commandBuffer.slice(cursorPos);
                cursorPos--;
                redrawInput();
            }
            break;
        case 'Delete':
            if (cursorPos < commandBuffer.length) {
                commandBuffer = commandBuffer.slice(0, cursorPos) + commandBuffer.slice(cursorPos + 1);
                redrawInput();
            }
            break;
        case 'ArrowLeft':
            if (cursorPos > 0) {
                cursorPos--;
                term.write('\x1b[D');
            }
            break;
        case 'ArrowRight':
            if (cursorPos < commandBuffer.length) {
                cursorPos++;
                term.write('\x1b[C');
            }
            break;
        case 'ArrowUp':
            if (historyIndex > 0) {
                historyIndex--;
                loadHistory();
            }
            break;
        case 'ArrowDown':
            if (historyIndex < history.length - 1) {
                historyIndex++;
                loadHistory();
            } else {
                historyIndex = history.length;
                commandBuffer = '';
                cursorPos = 0;
                redrawInput();
            }
            break;
        default:
            if (printable) {
                commandBuffer = commandBuffer.slice(0, cursorPos) + key + commandBuffer.slice(cursorPos);
                cursorPos++;
                redrawInput();
            }
    }
});

function printPrompt() {
    term.write(`\r\n${PROMPT}`);
}

function redrawInput() {
    term.write('\x1b[G');
    term.write(PROMPT + commandBuffer + ' ');
    const cursorMoveLeft = (commandBuffer.length - cursorPos + 1);
    if (cursorMoveLeft > 0) term.write(`\x1b[${cursorMoveLeft}D`);
}

function loadHistory() {
    commandBuffer = history[historyIndex] || '';
    cursorPos = commandBuffer.length;
    redrawInput();
}

async function handleCommand(cmd) {
    if (!cmd) return printPrompt();

    if (cmd === 'help') {
        try {
            const res = await fetch('/api/v1/tool/list');
            const data = await res.json();
            term.writeln('\nAvailable tools:');
            (data.tools || []).forEach(tool => term.writeln(`- ${tool}`));
        } catch {
            term.writeln('Error: Failed to fetch tool list.');
        }
        return printPrompt();
    }

    if (cmd === 'clear' || cmd === 'cls') {
        term.clear();
        commandBuffer = '';
        cursorPos = 0;
        printPrompt();
        return;
    }

    const [tool, ...args] = cmd.split(/\s+/);
    const formData = new FormData();
    formData.append('tool', tool);
    if (args.length) formData.append('args', args.join(' '));

    const filesInput = document.getElementById('files-input');
    if (filesInput && filesInput.files.length > 0) {
        for (const file of filesInput.files) {
            formData.append('files', file, file.webkitRelativePath || file.name);
        }
    }

    term.writeln(`\n# ${cmd}\n`);

    try {
        const res = await fetch('/api/v1/tool/run', {
            method: 'POST',
            body: formData
        });

        const json = await res.json();

        if (!res.ok) {
            let errorMsg = json.detail || json.error || 'Unknown error';
            term.writeln(`Error: ${typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg)}`);
            lastCommandOutput = `Error: ${errorMsg}`;
        } else {
            lastCommandOutput = '';
            if (json.stdout) {
                json.stdout.split('\n').forEach(line => term.writeln(line));
                lastCommandOutput += json.stdout + '\n';
            }
            if (json.stderr) {
                term.writeln('\n[stderr]');
                json.stderr.split('\n').forEach(line => term.writeln(line));
                lastCommandOutput += '\n[stderr]\n' + json.stderr + '\n';
            }
            term.writeln(`\n[exit code] ${json.exit_code}`);
            lastCommandOutput += `\n[exit code] ${json.exit_code}\n`;
        }
    } catch (err) {
        term.writeln(`Request failed: ${err.message}`);
        lastCommandOutput = `Request failed: ${err.message}`;
    }

    printPrompt();
}

async function exportLastResult() {
    if (!lastCommandOutput) return term.writeln('No command output to export.');

    try {
        if ('showSaveFilePicker' in window) {
            const opts = {
                types: [{ description: 'Text Files', accept: { 'text/plain': ['.txt'] } }],
            };
            const handle = await window.showSaveFilePicker(opts);
            const writable = await handle.createWritable();
            await writable.write(lastCommandOutput);
            await writable.close();
            term.writeln('Output saved successfully.');
        } else {
            const blob = new Blob([lastCommandOutput], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'cassanova-command-output.txt';
            a.click();
            URL.revokeObjectURL(url);
            term.writeln('Command output exported successfully.');
        }
    } catch (err) {
        term.writeln(`Error exporting file: ${err.message}`);
    }
}