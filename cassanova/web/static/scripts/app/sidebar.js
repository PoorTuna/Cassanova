document.addEventListener("DOMContentLoaded", () => {
    // --- Sidebar Toggle ---
    const toggleBtn = document.querySelector(".sidebar-toggle");
    const sidebar = document.querySelector(".sidebar");

    if (toggleBtn && sidebar) {
        const main = document.querySelector("main");

        const isCollapsed = localStorage.getItem("sidebarCollapsed") === "true";

        sidebar.style.transition = 'none';
        if (main) main.style.transition = 'none';

        if (isCollapsed) {
            sidebar.classList.add("collapsed");
        } else {
            sidebar.classList.remove("collapsed");
        }

        sidebar.offsetHeight;

        sidebar.style.transition = '';
        if (main) main.style.transition = '';

        toggleBtn.addEventListener("click", () => {
            sidebar.classList.toggle("collapsed");
            const currentlyCollapsed = sidebar.classList.contains("collapsed");
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
});
