// cluster-settings.js
(() => {
    const isBool = v => v === true || v === false || v === 'true' || v === 'false';
    const isNull = v => v === null || v === undefined || v === 'null';

    const typeClass = v => {
        if (isBool(v)) return 'type-bool ' + (v === true || v === 'true' ? 'true' : 'false');
        if (isNull(v)) return 'type-null';
        return '';
    };
    const MIN_GROUP_SIZE = 5;

    function groupByPrefix(data) {
        const groups = {};
        const generalGroup = {};

        // First, group keys by prefix (dot or underscore)
        for (const key in data) {
            let dotIdx = key.indexOf('.');
            let underscoreIdx = key.indexOf('_');

            // Find earliest separator index (dot or underscore)
            let firstSep = -1;
            if (dotIdx !== -1 && underscoreIdx !== -1) firstSep = Math.min(dotIdx, underscoreIdx);
            else if (dotIdx !== -1) firstSep = dotIdx;
            else if (underscoreIdx !== -1) firstSep = underscoreIdx;

            const groupName = firstSep !== -1 ? key.substring(0, firstSep) : 'General';
            groups[groupName] = groups[groupName] || {};
            groups[groupName][key] = data[key];
        }

        // Merge small groups (< MIN_GROUP_SIZE entries) into General
        for (const [groupName, entries] of Object.entries(groups)) {
            if (groupName === 'General') continue;
            if (Object.keys(entries).length < MIN_GROUP_SIZE) {
                Object.assign(generalGroup, entries);
                delete groups[groupName];
            }
        }

        groups['General'] = groups['General'] || {};
        Object.assign(groups['General'], generalGroup);

        // Now sort groups keys so "General" is first, then others alphabetically
        const sortedGroups = {};
        sortedGroups['General'] = groups['General'];

        Object.keys(groups)
            .filter(name => name !== 'General')
            .sort((a, b) => a.localeCompare(b))
            .forEach(name => {
                sortedGroups[name] = groups[name];
            });

        return sortedGroups;
    }

    function el(tag, attrs = {}, children = []) {
        const element = document.createElement(tag);
        for (const [k, v] of Object.entries(attrs)) {
            if (k === 'class') element.className = v;
            else if (k.startsWith('data-')) element.setAttribute(k, v);
            else if (k === 'text') element.textContent = v;
            else element.setAttribute(k, v);
        }
        children.forEach(c => element.appendChild(c));
        return element;
    }

    function copyText(text) {
        navigator.clipboard.writeText(text);
    }

    function createClipboardIcon() {
        const svgNS = "http://www.w3.org/2000/svg";
        const svg = document.createElementNS(svgNS, "svg");
        svg.setAttribute("fill", "none");
        svg.setAttribute("viewBox", "0 0 24 24");
        svg.setAttribute("stroke-width", "1.5");
        svg.setAttribute("stroke", "currentColor");

        const path = document.createElementNS(svgNS, "path");
        path.setAttribute("stroke-linecap", "round");
        path.setAttribute("stroke-linejoin", "round");
        path.setAttribute("d", "M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184");

        svg.appendChild(path);
        return svg;
    }

    function createSettingRow(key, value) {
        const keySpan = el('span', {class: 'cs-key', 'data-full': key, title: key, text: key});
        const valStr = (value === null || value === undefined) ? 'null' : String(value);
        const valSpan = el('span', {
            class: 'cs-value ' + typeClass(value),
            'data-full': valStr,
            title: valStr,
            text: valStr
        });
        const btn = el('button', {class: 'cs-copy-btn', title: `Copy ${key}`}, [createClipboardIcon()]);
        btn.onclick = e => {
            e.stopPropagation();
            copyText(`${key}: ${valStr}`);
        };
        return el('div', {class: 'cs-setting-item'}, [keySpan, valSpan, btn]);
    }

    function createGroupSection(name, settings) {
        const details = el('details', {class: 'cs-group', open: true});
        const summary = el('summary', {text: name});
        const list = el('div', {class: 'cs-settings-list'});
        Object.entries(settings).forEach(([k, v]) => list.appendChild(createSettingRow(k, v)));
        details.appendChild(summary);
        details.appendChild(list);
        return details;
    }

    function render(data) {
        const container = document.getElementById('cs-groupsContainer');
        container.innerHTML = '';
        const grouped = groupByPrefix(data);
        Object.entries(grouped).forEach(([name, settings]) => {
            container.appendChild(createGroupSection(name, settings));
        });
    }

    function setupSearch() {
        document.getElementById('cs-searchInput').addEventListener('input', e => {
            const filter = e.target.value.toLowerCase();
            document.querySelectorAll('.cs-group').forEach(group => {
                let visibleCount = 0;
                group.querySelectorAll('.cs-setting-item').forEach(item => {
                    const k = item.querySelector('.cs-key').textContent.toLowerCase();
                    const v = item.querySelector('.cs-value').textContent.toLowerCase();
                    const match = k.includes(filter) || v.includes(filter);
                    item.style.display = match ? 'flex' : 'none';
                    if (match) visibleCount++;
                });
                group.style.display = visibleCount > 0 ? '' : 'none';
            });
        });
    }

    render(settingsData);
    setupSearch();
})();
