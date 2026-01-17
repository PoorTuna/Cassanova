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

    const particles = Array.from({ length: 120 }, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: Math.random() * 2 + 0.5,
        dx: Math.random() * 0.4 - 0.2,
        dy: Math.random() * 0.4 - 0.2
    }));

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Get theme color
        const computedStyle = getComputedStyle(document.body);
        const primaryColor = computedStyle.getPropertyValue('--color-primary').trim() || '#4fc3f7';

        ctx.fillStyle = primaryColor;
        ctx.strokeStyle = primaryColor;

        particles.forEach((p, i) => {
            ctx.globalAlpha = 0.4;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fill();

            // Connections
            for (let j = i + 1; j < particles.length; j++) {
                const p2 = particles[j];
                const dist = Math.sqrt((p.x - p2.x) ** 2 + (p.y - p2.y) ** 2);
                if (dist < 120) {
                    ctx.globalAlpha = (1 - dist / 120) * 0.15;
                    ctx.beginPath();
                    ctx.moveTo(p.x, p.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.stroke();
                }
            }

            p.x += p.dx;
            p.y += p.dy;

            if (p.x < 0 || p.x > canvas.width) p.dx *= -1;
            if (p.y < 0 || p.y > canvas.height) p.dy *= -1;
        });
        requestAnimationFrame(animate);
    }

    animate();
});