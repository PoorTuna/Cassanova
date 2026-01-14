document.addEventListener("DOMContentLoaded", () => {
    // Attach listener to all elements with 'copyable' class
    document.addEventListener('click', async (e) => {
        const target = e.target.closest('.copyable');
        if (!target) return;

        e.preventDefault();
        e.stopPropagation();

        // Determine content to copy
        const textToCopy = target.dataset.copy || target.querySelector('span')?.textContent || target.textContent;

        if (!textToCopy) return;

        try {
            await navigator.clipboard.writeText(textToCopy.trim());
            showCopiedFeedback(target);
        } catch (err) {
            console.error('Failed to copy text: ', err);
        }
    });

    function showCopiedFeedback(element) {
        // Create a fixed tooltip appended to body to avoid overflow clipping
        let tooltip = document.createElement('div');
        tooltip.className = 'copy-tooltip-fixed';
        tooltip.textContent = 'Copied!';
        document.body.appendChild(tooltip);

        // Position it relative to the clicked element
        const rect = element.getBoundingClientRect();

        // Calculate position (centered above element)
        const top = rect.top - 40; // 40px above
        const left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2);

        tooltip.style.top = `${top}px`;
        tooltip.style.left = `${left}px`;
        tooltip.style.opacity = '1';
        tooltip.style.transform = 'translateY(0)';

        // Remove after delay
        setTimeout(() => {
            tooltip.style.opacity = '0';
            tooltip.style.transform = 'translateY(10px)';
            setTimeout(() => {
                if (tooltip.parentNode) {
                    tooltip.parentNode.removeChild(tooltip);
                }
            }, 300); // match transition duration
        }, 1200);
    }
});
