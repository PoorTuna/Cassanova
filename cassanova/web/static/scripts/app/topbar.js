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

    // --- Theme Switching (dot grid in user dropdown) ---
    const themeGrid = document.getElementById('topbar-theme-grid');
    if (themeGrid) {
        const dots = themeGrid.querySelectorAll('.topbar-theme-dot');

        let savedTheme = localStorage.getItem('selectedTheme') || 'dark';
        applyTheme(savedTheme);
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

    function applyTheme(theme) {
        document.documentElement.classList.forEach(cls => {
            if (cls.endsWith('-theme')) {
                document.documentElement.classList.remove(cls);
            }
        });
        document.documentElement.classList.add(`${theme}-theme`);
    }
});
