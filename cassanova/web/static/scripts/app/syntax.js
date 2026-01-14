/**
 * Highlight JSON syntax with HTML spans.
 * @param {Object|string} json - The JSON object or string to highlight.
 * @returns {string} HTML string with highlighted syntax.
 */
function syntaxHighlight(json) {
    if (typeof json !== 'string') {
        json = JSON.stringify(json, null, 2);
    }

    // Escape HTML entities to prevent XSS/rendering issues
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
        let cls = 'syntax-number';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'syntax-key';
            } else {
                cls = 'syntax-string';
                // Improve formatting for long strings with escaped newlines (like SQL schemas)
                match = match.replace(/\\n/g, '<br>').replace(/\\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;');
            }
        } else if (/true|false/.test(match)) {
            cls = 'syntax-boolean';
        } else if (/null/.test(match)) {
            cls = 'syntax-null';
        }
        return '<span class="' + cls + '">' + match + '</span>';
    });
}

// Attach to window for global access
window.syntaxHighlight = syntaxHighlight;
