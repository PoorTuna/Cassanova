/**
 * SSTable Smasher - A Cassandra-themed LSM Compaction Minigame
 * Lightweight Canvas Implementation (No Engine)
 */

class SSTableSmasher {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.width = this.canvas.width = 600;
        this.height = this.canvas.height = 600;
        this.centerX = this.width / 2;
        this.centerY = this.height / 2;

        // Grid Constants
        this.numSectors = 12; // 12 Token Buckets
        this.innerRadius = 80;
        this.rowHeight = 22;
        this.maxRows = 8;
        this.blockSize = 18;

        this.levels = {
            0: { color: '#71717a', label: 'L0', score: 10 },
            1: { color: '#06b6d4', label: 'L1', score: 50 },
            2: { color: '#8b5cf6', label: 'L2', score: 250 },
            3: { color: '#10b981', label: 'L3', score: 1250 }
        };

        // Game State
        this.buckets = Array.from({ length: this.numSectors }, () => []);
        this.currentSector = 0;
        this.score = 0;
        this.latency = 0;
        this.isGameOver = false;
        this.isPaused = true;
        this.dropCount = 0;

        this.bindEvents();
    }

    bindEvents() {
        window.addEventListener('keydown', (e) => {
            if (document.getElementById('game-modal').classList.contains('hidden')) return;

            const gameKeys = ['Space', 'ArrowLeft', 'ArrowRight'];
            if (gameKeys.includes(e.code)) e.preventDefault();

            if (this.isPaused || this.isGameOver) {
                if (e.code === 'Space') {
                    const overlay = document.getElementById('game-start-overlay');
                    if (overlay) overlay.classList.add('hidden');
                    this.start();
                }
                return;
            }

            if (e.code === 'ArrowLeft') {
                this.currentSector = (this.currentSector - 1 + this.numSectors) % this.numSectors;
            }
            if (e.code === 'ArrowRight') {
                this.currentSector = (this.currentSector + 1) % this.numSectors;
            }
            if (e.code === 'Space') {
                this.dropTable();
            }
        });
    }

    start() {
        this.isPaused = false;
        this.isGameOver = false;
        this.score = 0;
        this.latency = 0;
        this.dropCount = 0;
        this.buckets = Array.from({ length: this.numSectors }, () => []);
        this.loop();
    }

    dropTable() {
        const bucket = this.buckets[this.currentSector];
        if (bucket.length >= this.maxRows) {
            this.isGameOver = true;
            return;
        }

        // Fallback: hide start overlay if it's still visible
        const startOverlay = document.getElementById('game-start-overlay');
        if (startOverlay && !startOverlay.classList.contains('hidden')) {
            startOverlay.classList.add('hidden');
        }

        // Process GC Grace Period for all existing tombstones
        this.processGCGrace();

        this.dropCount++;

        // 25% chance of a Tombstone - Scaled for higher difficulty
        const isTombstone = Math.random() < 0.25;

        const newTable = {
            level: isTombstone ? 'T' : 0,
            compacting: false,
            turnsLeft: isTombstone ? 10 : -1 // gc_grace_period = 10 turns
        };

        bucket.push(newTable);

        if (!isTombstone) {
            this.checkCompaction(this.currentSector);
        }

        this.calculateLatency();
        this.score += 5;
        if (window.updateGameScore) window.updateGameScore(this.score, this.latency);
    }

    processGCGrace() {
        // Decrement turns for all tombstones in all buckets
        this.buckets.forEach((bucket, idx) => {
            let reclaimedCount = 0;
            for (let i = bucket.length - 1; i >= 0; i--) {
                const table = bucket[i];
                if (table.level === 'T') {
                    table.turnsLeft--;
                    if (table.turnsLeft <= 0) {
                        // GC Grace Expired! Mutate into L0 SSTable
                        table.level = 0;
                        table.turnsLeft = -1;
                        this.score += 50;
                        reclaimedCount++;
                    }
                }
            }
            if (reclaimedCount > 0) {
                this.triggerStatus('GC_GRACE EXPIRED: TOMBSTONE PURGED', '#10b981');
                // Check if the mutation allowed a new compaction
                this.checkCompaction(idx);
            }
        });
    }

    checkCompaction(sectorIdx) {
        const bucket = this.buckets[sectorIdx];
        if (bucket.length < 4) return;

        // Pattern matching: search for 4 blocks of same level in stack
        for (let i = 0; i <= bucket.length - 4; i++) {
            const level = bucket[i].level;
            if (level === 'T' || level === 3) continue; // Tomstones & Max Level don't compact

            const isMatch = bucket.slice(i, i + 4).every(t => t.level === level);
            if (isMatch) {
                // Perform Compaction
                const nextLevel = level + 1;
                bucket.splice(i, 4, { level: nextLevel, compacting: true });

                this.score += (level + 1) * 100;
                this.triggerStatus('COMPACTING...', '#fbbf24');

                // Recursive check
                setTimeout(() => {
                    bucket[i].compacting = false;
                    this.checkCompaction(sectorIdx);
                    this.calculateLatency();
                    if (window.updateGameScore) window.updateGameScore(this.score, this.latency);
                }, 400);
                return;
            }
        }
    }

    calculateLatency() {
        // Latency = Sum of (SSTables + Tombstones*2) across all buckets
        let totalLoad = 0;
        this.buckets.forEach(b => {
            b.forEach(t => {
                totalLoad += (t.level === 'T') ? 5 : 1;
            });
        });

        this.latency = Math.round((totalLoad / (this.numSectors * this.maxRows)) * 100);
    }

    triggerStatus(text, color) {
        const statusEl = document.querySelector('.stat-item span[style*="color: var(--color-success)"]');
        if (statusEl) {
            statusEl.textContent = text;
            statusEl.style.color = color;
            setTimeout(() => {
                statusEl.textContent = 'NOMINAL';
                statusEl.style.color = 'var(--color-success)';
            }, 800);
        }
    }

    draw() {
        this.ctx.clearRect(0, 0, this.width, this.height);

        // 1. Draw Ring structure
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        this.ctx.setLineDash([]);
        for (let i = 0; i < this.numSectors; i++) {
            const angle = (i / this.numSectors) * Math.PI * 2;
            this.ctx.beginPath();
            this.ctx.moveTo(this.centerX, this.centerY);
            this.ctx.lineTo(
                this.centerX + Math.cos(angle) * 300,
                this.centerY + Math.sin(angle) * 300
            );
            this.ctx.stroke();
        }

        // 2. Draw Buckets content
        this.buckets.forEach((bucket, sIdx) => {
            const baseAngle = ((sIdx + 0.5) / this.numSectors) * Math.PI * 2;

            bucket.forEach((table, rIdx) => {
                const dist = this.innerRadius + (rIdx * this.rowHeight);
                const x = this.centerX + Math.cos(baseAngle) * dist;
                const y = this.centerY + Math.sin(baseAngle) * dist;

                this.ctx.save();
                this.ctx.translate(x, y);
                this.ctx.rotate(baseAngle);

                const isT = table.level === 'T';
                const config = isT ? { color: '#ef4444', label: 'T' } : this.levels[table.level];

                this.ctx.fillStyle = config.color;
                this.ctx.strokeStyle = '#fff';
                this.ctx.lineWidth = table.compacting ? 2 : 0.5;

                if (table.compacting) {
                    this.ctx.shadowBlur = 15;
                    this.ctx.shadowColor = config.color;
                }

                this.ctx.fillRect(-this.blockSize / 2, -this.blockSize / 2, this.blockSize, this.blockSize);
                this.ctx.strokeRect(-this.blockSize / 2, -this.blockSize / 2, this.blockSize, this.blockSize);

                // Label
                this.ctx.fillStyle = '#fff';
                this.ctx.font = '800 10px JetBrains Mono';
                this.ctx.textAlign = 'center';
                this.ctx.textBaseline = 'middle';
                this.ctx.fillText(config.label, 0, 0);

                // Tombstone countdown
                if (isT) {
                    this.ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
                    this.ctx.font = '700 7px JetBrains Mono';
                    this.ctx.textAlign = 'right';
                    this.ctx.fillText(table.turnsLeft, 7, 7);
                }

                this.ctx.restore();
            });
        });

        // 3. Draw "Current Selection" Guide
        const activeAngle = ((this.currentSector + 0.5) / this.numSectors) * Math.PI * 2;
        this.ctx.strokeStyle = 'var(--color-primary)';
        this.ctx.setLineDash([5, 2]);
        this.ctx.lineWidth = 1;
        this.ctx.beginPath();
        this.ctx.arc(this.centerX, this.centerY, this.innerRadius + (this.buckets[this.currentSector].length * this.rowHeight), activeAngle - 0.2, activeAngle + 0.2);
        this.ctx.stroke();

        // Guide Line to Injector
        this.ctx.beginPath();
        this.ctx.moveTo(this.centerX, this.centerY);
        this.ctx.lineTo(this.centerX + Math.cos(activeAngle) * 50, this.centerY + Math.sin(activeAngle) * 50);
        this.ctx.stroke();

        if (this.isGameOver) {
            this.ctx.fillStyle = 'rgba(0,0,0,0.8)';
            this.ctx.fillRect(0, 0, this.width, this.height);
            this.ctx.fillStyle = '#fff';
            this.ctx.font = '800 32px JetBrains Mono';
            this.ctx.textAlign = 'center';
            this.ctx.fillText('NODE CRASHED', this.centerX, this.centerY - 20);
            this.ctx.font = '14px JetBrains Mono';
            this.ctx.fillText('BLOOM FILTER OVERLOAD / DISK FULL', this.centerX, this.centerY + 20);
            this.ctx.fillText('PRESS SPACE TO REBOOT', this.centerX, this.centerY + 60);
        }
    }

    loop() {
        if (this.isPaused) return;
        this.draw();
        requestAnimationFrame(() => this.loop());
    }
}

// Global accessor for the game instance
window.initGame = () => {
    const game = new SSTableSmasher('game-canvas');
    window.gameInstance = game;

    window.updateGameScore = (score, latency) => {
        const scoreEl = document.getElementById('game-score-val');
        if (scoreEl) scoreEl.textContent = score;

        const latVal = document.getElementById('latency-val');
        if (latVal) {
            latVal.textContent = latency + 'ms';
            latVal.style.color = latency > 60 ? '#ef4444' : (latency > 30 ? '#fbbf24' : '#10b981');
        }
    };
};
