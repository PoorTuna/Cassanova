document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('refresh-toggle');
    const dropdown = document.getElementById('refresh-dropdown');
    const icon = document.getElementById('refresh-icon');
    const label = document.getElementById('refresh-label');

    if (!toggle || !dropdown) return;

    const STORAGE_KEY = 'cassanova_refresh_interval';
    const DEFAULT_INTERVAL = 60000;
    const LABELS = { 0: 'Off', 5000: '5s', 15000: '15s', 30000: '30s', 60000: '1m', 300000: '5m' };

    let currentInterval = parseInt(localStorage.getItem(STORAGE_KEY), 10);
    if (isNaN(currentInterval) || !(currentInterval in LABELS)) {
        currentInterval = DEFAULT_INTERVAL;
    }

    let timerId = null;

    function updateUI() {
        label.textContent = 'Refresh: ' + LABELS[currentInterval];

        dropdown.querySelectorAll('.refresh-option').forEach(opt => {
            const val = parseInt(opt.dataset.interval, 10);
            opt.classList.toggle('active', val === currentInterval);
        });
    }

    function startTimer() {
        stopTimer();
        if (currentInterval > 0) {
            timerId = setInterval(doRefresh, currentInterval);
        }
    }

    function stopTimer() {
        if (timerId) {
            clearInterval(timerId);
            timerId = null;
        }
    }

    function doRefresh() {
        if (document.hidden) return;

        icon.classList.add('spinning');

        if (typeof window.cassanovaRefresh === 'function') {
            try {
                const result = window.cassanovaRefresh();
                if (result && typeof result.finally === 'function') {
                    result.finally(() => icon.classList.remove('spinning'));
                } else {
                    setTimeout(() => icon.classList.remove('spinning'), 1000);
                }
            } catch (e) {
                icon.classList.remove('spinning');
            }
        } else {
            location.reload();
        }
    }

    function selectInterval(ms) {
        currentInterval = ms;
        localStorage.setItem(STORAGE_KEY, String(ms));
        updateUI();
        startTimer();
        dropdown.classList.add('hidden');
    }

    // Toggle dropdown
    toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('hidden');
    });

    // Select interval
    dropdown.querySelectorAll('.refresh-option').forEach(opt => {
        opt.addEventListener('click', (e) => {
            e.stopPropagation();
            selectInterval(parseInt(opt.dataset.interval, 10));
        });
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
        if (!dropdown.contains(e.target) && e.target !== toggle) {
            dropdown.classList.add('hidden');
        }
    });

    // Pause/resume on tab visibility
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            stopTimer();
        } else {
            startTimer();
        }
    });

    // Initialize
    updateUI();
    startTimer();

    // Expose for manual trigger
    window.AutoRefresh = { refresh: doRefresh };
});
