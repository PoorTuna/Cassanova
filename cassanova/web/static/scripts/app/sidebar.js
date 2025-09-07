document.addEventListener("DOMContentLoaded", () => {
    // --- Sidebar Toggle ---
    const toggleBtn = document.querySelector(".sidebar-toggle");
    const sidebar = document.querySelector(".sidebar");

    toggleBtn.addEventListener("click", () => {
        sidebar.classList.toggle("collapsed");
        const expanded = !sidebar.classList.contains("collapsed");
        toggleBtn.setAttribute("aria-expanded", expanded);
    });

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
