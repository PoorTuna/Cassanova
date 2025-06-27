const form = document.getElementById('external_tools-form');
const outputSection = document.getElementById('output');
const stdoutPre = document.getElementById('stdout');
const stderrPre = document.getElementById('stderr');
const exitCodePre = document.getElementById('exit-code');

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Hide previous output and clear
    outputSection.hidden = true;
    stdoutPre.textContent = '';
    stderrPre.textContent = '';
    exitCodePre.textContent = '';

    const formData = new FormData(form);

    try {
        const resp = await fetch('/api/v1/tool/run', {
            method: 'POST',
            body: formData,
        });

        const json = await resp.json();

        if (!resp.ok) {
            // Display server error messages (including validation errors)
            const errorMsg = json.detail
                ? (Array.isArray(json.detail)
                    ? json.detail.map(e => e.msg).join('; ')
                    : json.detail)
                : json.error || JSON.stringify(json);
            alert(`Error ${resp.status}: ${errorMsg}`);
            return;
        }

        // Display tool output
        stdoutPre.textContent = json.stdout || '(no output)';
        stderrPre.textContent = json.stderr || '(no errors)';
        exitCodePre.textContent = json.exit_code;

        outputSection.hidden = false;
        outputSection.focus();

    } catch (err) {
        alert(`Network error: ${err.message}`);
    }
});
