document.addEventListener('DOMContentLoaded', () => {
    const el = document.querySelector('[data-current-cluster]');
    if (!el) return;

    const name = el.dataset.currentCluster;
    if (!name) return;

    let hash = 0;
    for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    const hue = Math.abs(hash) % 360;
    const color = `hsl(${hue}, 70%, 55%)`;

    const size = 32;
    const c = document.createElement('canvas');
    c.width = size;
    c.height = size;
    const ctx = c.getContext('2d');

    // Dark circle background
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2);
    ctx.fillStyle = '#121216';
    ctx.fill();

    // Colored ring
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, size / 2 - 2, 0, Math.PI * 2);
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.stroke();

    // First letter of cluster name
    ctx.fillStyle = color;
    ctx.font = 'bold 16px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(name.charAt(0).toUpperCase(), size / 2, size / 2 + 1);

    const link = document.querySelector('link[rel="icon"]');
    if (link) link.href = c.toDataURL();
});
