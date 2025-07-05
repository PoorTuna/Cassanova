const filterInput = document.getElementById('cluster-filter');
const clusterRows = document.querySelectorAll('.cluster-row');

filterInput.addEventListener('input', () => {
    const term = filterInput.value.trim().toLowerCase();
    clusterRows.forEach(row => {
        const name = row.dataset.name;
        row.hidden = !name.includes(term);
    });
});

        // Particle background animation
        document.addEventListener("DOMContentLoaded", () => {
            const canvas = document.getElementById("bg-particles");
            if (!canvas) return;

            const ctx = canvas.getContext("2d");
            function resize() {
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
            }
            resize();
            window.addEventListener("resize", resize);

            const particles = Array.from({ length: 60 }, () => ({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                r: Math.random() * 1.2 + 0.5,
                dx: Math.random() * 0.2 - 0.1,
                dy: Math.random() * 0.2 - 0.1
            }));

            function animate() {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = "rgba(79, 195, 247, 0.35)";
                particles.forEach(p => {
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                    ctx.fill();

                    p.x += p.dx;
                    p.y += p.dy;

                    if (p.x < 0 || p.x > canvas.width) p.dx *= -1;
                    if (p.y < 0 || p.y > canvas.height) p.dy *= -1;
                });
                requestAnimationFrame(animate);
            }

            animate();
        });