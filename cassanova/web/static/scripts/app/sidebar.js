document.addEventListener("DOMContentLoaded", () => {
    // --- Sidebar Toggle ---
    const toggleBtn = document.querySelector(".sidebar-toggle");
    const sidebar = document.querySelector(".sidebar");

    if (toggleBtn && sidebar) {
        const main = document.querySelector("main");

        // Load sidebar state (default to expanded/not-collapsed if null)
        const isCollapsed = localStorage.getItem("sidebarCollapsed") === "true";

        // Temporarily disable transitions to prevent jump-animation on load
        sidebar.style.transition = 'none';
        if (main) main.style.transition = 'none';

        if (isCollapsed) {
            sidebar.classList.add("collapsed");
            toggleBtn.setAttribute("aria-expanded", "false");
        } else {
            sidebar.classList.remove("collapsed");
            toggleBtn.setAttribute("aria-expanded", "true");
        }

        // Force a reflow to apply state without transition
        sidebar.offsetHeight;

        // Re-enable transitions for future interactions
        sidebar.style.transition = '';
        if (main) main.style.transition = '';

        toggleBtn.addEventListener("click", () => {
            sidebar.classList.toggle("collapsed");
            const currentlyCollapsed = sidebar.classList.contains("collapsed");
            toggleBtn.setAttribute("aria-expanded", !currentlyCollapsed);
            localStorage.setItem("sidebarCollapsed", currentlyCollapsed);
        });
    }

    // --- Highlight Active Link ---
    const links = document.querySelectorAll(".sidebar-link");
    const currentPath = window.location.pathname;
    links.forEach(link => {
        if (link.getAttribute("href") === currentPath) {
            link.classList.add("active");
        }
    });

    // --- Theme Selector ---
    const themeDotWrapper = document.querySelector('.theme-dot-wrapper');
    const themeDot = document.getElementById('theme-dot');
    const themeDropdown = document.getElementById('theme-dropdown');
    const themeLabel = document.querySelector('.theme-label');
    const themeOptions = document.querySelectorAll('.theme-option');

    if (themeDotWrapper && themeDot && themeDropdown && themeLabel && themeOptions.length > 0) {
        // Load theme from localStorage
        let savedTheme = localStorage.getItem('selectedTheme');
        if (!savedTheme) {
            savedTheme = 'dark'; // default theme
            localStorage.setItem('selectedTheme', savedTheme);
        }
        applyTheme(savedTheme);

        // Toggle dropdown
        themeDotWrapper.addEventListener('click', () => {
            themeDropdown.classList.toggle('hidden');
        });

        // Select a theme
        themeOptions.forEach(option => {
            option.addEventListener('click', () => {
                const selectedTheme = option.dataset.theme;
                applyTheme(selectedTheme);
                themeDropdown.classList.add('hidden');

                // Save to localStorage
                localStorage.setItem('selectedTheme', selectedTheme);
            });
        });

        // Click outside to close dropdown
        document.addEventListener('click', e => {
            if (!themeDotWrapper.contains(e.target) && !themeDropdown.contains(e.target)) {
                themeDropdown.classList.add('hidden');
            }
        });
    }

    // --- Apply Theme Function ---
    function applyTheme(theme) {
        const option = Array.from(themeOptions).find(opt => opt.dataset.theme === theme);
        if (!option) return;

        // Update dot color
        const dotColor = getComputedStyle(option.querySelector('.theme-preview')).backgroundColor;
        themeDot.style.background = dotColor;

        // Update label text
        themeLabel.textContent = option.querySelector('.theme-name').textContent;

        // Remove any existing theme classes (dynamic)
        document.documentElement.classList.forEach(cls => {
            if (cls.endsWith('-theme')) {
                document.documentElement.classList.remove(cls);
            }
        });

        // Apply the selected theme
        document.documentElement.classList.add(`${theme}-theme`);
    }
});
