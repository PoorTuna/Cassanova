document.addEventListener("DOMContentLoaded", () => {
    const toggleBtn = document.querySelector(".sidebar-toggle");
    const sidebar = document.querySelector(".sidebar");

    toggleBtn.addEventListener("click", () => {
        sidebar.classList.toggle("collapsed");
        const expanded = !sidebar.classList.contains("collapsed");
        toggleBtn.setAttribute("aria-expanded", expanded);
    });

    // Highlight active link
    const links = document.querySelectorAll(".sidebar-link");
    const currentPath = window.location.pathname;
    links.forEach(link => {
        if (link.getAttribute("href") === currentPath) {
            link.classList.add("active");
        }
    });
});
