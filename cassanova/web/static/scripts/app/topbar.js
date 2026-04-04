document.addEventListener("DOMContentLoaded", () => {
    // --- User Dropdown ---
    const userBtn = document.getElementById('topbar-user-btn');
    const userDropdown = document.getElementById('topbar-user-dropdown');

    if (userBtn && userDropdown) {
        userBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            userDropdown.classList.toggle('hidden');
        });

        document.addEventListener('click', (e) => {
            if (!userDropdown.contains(e.target) && !userBtn.contains(e.target)) {
                userDropdown.classList.add('hidden');
            }
        });
    }

    // --- Theme Application (always, even on pages without the grid) ---
    function applyTheme(theme) {
        document.documentElement.classList.forEach(cls => {
            if (cls.endsWith('-theme')) {
                document.documentElement.classList.remove(cls);
            }
        });
        document.documentElement.classList.add(`${theme}-theme`);
    }

    const savedTheme = localStorage.getItem('selectedTheme') || 'dark';
    applyTheme(savedTheme);

    // --- Theme Switching (dot grid in user dropdown) ---
    const themeGrid = document.getElementById('topbar-theme-grid');
    if (themeGrid) {
        const dots = themeGrid.querySelectorAll('.topbar-theme-dot');
        markActiveDot(savedTheme);

        dots.forEach(dot => {
            dot.addEventListener('click', (e) => {
                e.stopPropagation();
                const theme = dot.dataset.theme;
                applyTheme(theme);
                markActiveDot(theme);
                localStorage.setItem('selectedTheme', theme);
            });
        });

        function markActiveDot(theme) {
            dots.forEach(d => d.classList.remove('active'));
            const active = themeGrid.querySelector(`[data-theme="${theme}"]`);
            if (active) active.classList.add('active');
        }
    }

    // --- Search ---
    const searchInput = document.querySelector('.topbar-search');
    const searchWrapper = document.querySelector('.topbar-search-wrapper');

    if (searchInput && searchWrapper) {
        let searchIndex = [];
        let cacheTimestamp = 0;
        let fetchPromise = null;
        let activeIndex = -1;
        let dropdown = null;
        const currentCluster = searchWrapper.dataset.currentCluster || '';
        const CACHE_TTL = 60000;
        const MAX_RESULTS = 20;

        function createDropdown() {
            if (dropdown) return dropdown;
            dropdown = document.createElement('div');
            dropdown.className = 'search-dropdown hidden';
            dropdown.id = 'search-dropdown';
            searchWrapper.appendChild(dropdown);
            return dropdown;
        }

        function buildSearchIndex(clusterNames, schemaMaps) {
            const items = [];

            // Global pages
            items.push({ type: 'page', label: 'All Clusters', cluster: '', keyspace: null, url: '/', searchText: 'all clusters home' });
            items.push({ type: 'page', label: 'Tools', cluster: '', keyspace: null, url: '/tools', searchText: 'tools terminal' });

            for (const cluster of clusterNames) {
                // Pages per cluster
                const pages = [
                    { label: 'Cluster Overview', path: '', extra: 'overview dashboard' },
                    { label: 'Nodes', path: '/nodes', extra: 'nodes servers' },
                    { label: 'VNodes', path: '/vnodes', extra: 'vnodes tokens virtual' },
                    { label: 'CQL Shell', path: '/tools/cqlsh', extra: 'cql query shell console' },
                    { label: 'Users', path: '/users', extra: 'users roles permissions auth' },
                    { label: 'Settings', path: '/settings', extra: 'settings configuration' },
                ];
                for (const page of pages) {
                    items.push({
                        type: 'page',
                        label: page.label,
                        cluster,
                        keyspace: null,
                        url: `/cluster/${encodeURIComponent(cluster)}${page.path}`,
                        searchText: `${page.label} ${cluster} ${page.extra}`.toLowerCase(),
                    });
                }

                // Keyspaces and tables
                const schema = schemaMaps[cluster];
                if (!schema) continue;

                for (const [ks, tables] of Object.entries(schema)) {
                    items.push({
                        type: 'keyspace',
                        label: ks,
                        cluster,
                        keyspace: null,
                        url: `/cluster/${encodeURIComponent(cluster)}/keyspace/${encodeURIComponent(ks)}`,
                        searchText: `${ks} ${cluster}`.toLowerCase(),
                    });

                    for (const table of Object.keys(tables)) {
                        items.push({
                            type: 'table',
                            label: table,
                            cluster,
                            keyspace: ks,
                            url: `/cluster/${encodeURIComponent(cluster)}/keyspace/${encodeURIComponent(ks)}/table/${encodeURIComponent(table)}/explore`,
                            searchText: `${table} ${ks} ${cluster}`.toLowerCase(),
                        });
                    }
                }
            }

            return items;
        }

        async function fetchSearchData() {
            const now = Date.now();
            if (searchIndex.length > 0 && (now - cacheTimestamp) < CACHE_TTL) return;
            if (fetchPromise) return fetchPromise;

            fetchPromise = (async () => {
                try {
                    const keysRes = await fetch('/api/v1/cluster-keys');
                    if (!keysRes.ok) return;
                    const clusterNames = await keysRes.json();

                    const schemaMaps = {};
                    await Promise.allSettled(
                        clusterNames.map(async (name) => {
                            try {
                                const res = await fetch(`/api/v1/cluster/${encodeURIComponent(name)}/schema-map`);
                                if (res.ok) schemaMaps[name] = await res.json();
                            } catch (_) { /* cluster unreachable */ }
                        })
                    );

                    searchIndex = buildSearchIndex(clusterNames, schemaMaps);
                    cacheTimestamp = Date.now();
                } catch (_) { /* network error */ }
                finally { fetchPromise = null; }
            })();

            return fetchPromise;
        }

        function filterResults(query) {
            if (!query) return [];
            const q = query.toLowerCase();

            let matched = searchIndex.filter(item => item.searchText.includes(q));

            // If not connected to a cluster, hide cluster-specific pages
            if (!currentCluster) {
                matched = matched.filter(item => item.type !== 'page' || !item.cluster);
            }

            // Sort: current cluster first, then prefix matches before substring matches
            matched.sort((a, b) => {
                const aCurrent = a.cluster === currentCluster ? 0 : 1;
                const bCurrent = b.cluster === currentCluster ? 0 : 1;
                if (aCurrent !== bCurrent) return aCurrent - bCurrent;

                const aPrefix = a.searchText.startsWith(q) ? 0 : 1;
                const bPrefix = b.searchText.startsWith(q) ? 0 : 1;
                return aPrefix - bPrefix;
            });

            // Cap per category
            const pages = matched.filter(i => i.type === 'page').slice(0, 5);
            const keyspaces = matched.filter(i => i.type === 'keyspace').slice(0, 5);
            const tables = matched.filter(i => i.type === 'table').slice(0, 10);

            return [...pages, ...keyspaces, ...tables];
        }

        function renderResults(results) {
            createDropdown();
            activeIndex = -1;

            if (results.length === 0) {
                const q = searchInput.value.trim();
                dropdown.innerHTML = q
                    ? '<div class="search-empty">No results found</div>'
                    : '<div class="search-empty">Start typing to search...</div>';
                dropdown.classList.remove('hidden');
                return;
            }

            let html = '';
            let globalIndex = 0;
            const categories = [
                { key: 'page', label: 'Navigation' },
                { key: 'keyspace', label: 'Keyspaces' },
                { key: 'table', label: 'Tables' },
            ];

            for (const cat of categories) {
                const items = results.filter(r => r.type === cat.key);
                if (items.length === 0) continue;

                html += `<div class="search-category-label">${cat.label}</div>`;
                for (const item of items) {
                    const meta = item.type === 'table'
                        ? `${escapeHtml(item.cluster)} / ${escapeHtml(item.keyspace)}`
                        : item.cluster ? escapeHtml(item.cluster) : '';

                    html += `<a class="search-result" href="${escapeHtml(item.url)}" data-index="${globalIndex}">`;
                    html += `<span class="search-result-label">${escapeHtml(item.label)}</span>`;
                    if (meta) html += `<span class="search-result-meta">${meta}</span>`;
                    html += `</a>`;
                    globalIndex++;
                }
            }

            dropdown.innerHTML = html;
            dropdown.classList.remove('hidden');
        }

        function setActive(index) {
            const items = dropdown ? dropdown.querySelectorAll('.search-result') : [];
            if (items.length === 0) return;

            items.forEach(i => i.classList.remove('active'));
            activeIndex = ((index % items.length) + items.length) % items.length;
            items[activeIndex].classList.add('active');
            items[activeIndex].scrollIntoView({ block: 'nearest' });
        }

        function closeDropdown() {
            if (dropdown) dropdown.classList.add('hidden');
            activeIndex = -1;
        }

        // Events
        searchInput.addEventListener('focus', async () => {
            await fetchSearchData();
            const q = searchInput.value.trim();
            renderResults(filterResults(q));
        });

        searchInput.addEventListener('input', () => {
            const q = searchInput.value.trim();
            renderResults(filterResults(q));
        });

        searchInput.addEventListener('keydown', (e) => {
            if (!dropdown || dropdown.classList.contains('hidden')) return;

            const items = dropdown.querySelectorAll('.search-result');

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setActive(activeIndex + 1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setActive(activeIndex - 1);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (activeIndex >= 0 && items[activeIndex]) {
                    window.location.href = items[activeIndex].getAttribute('href');
                }
            } else if (e.key === 'Escape') {
                closeDropdown();
                searchInput.value = '';
                searchInput.blur();
            }
        });

        document.addEventListener('click', (e) => {
            if (!searchWrapper.contains(e.target)) {
                closeDropdown();
            }
        });

        // Ctrl+K / Cmd+K global shortcut
        document.addEventListener('keydown', (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                searchInput.focus();
                searchInput.select();
            }
        });
    }
});
