/**
 * SSTable Smasher - Cassandra LSM Compaction Minigame
 * Single-file canvas implementation. No external deps.
 *
 * Layout: constants -> level config -> tile factory -> game class.
 * Turn pipeline: shadow ticks -> GC grace -> piece placement ->
 *                compaction -> queue advance -> housekeeping.
 */

// ===== Constants =====
const NUM_SECTORS = 12;
const MAX_ROWS = 8;
const INNER_RADIUS = 80;
const ROW_HEIGHT = 22;
const BLOCK_SIZE = 18;

const GC_GRACE = 10;
const SHADOW_TURNS = 3;
const COMBO_WINDOW_MS = 1000;
const COMBO_CAP = 8;
const CHAIN_DELAY_MS = 400;
const MAX_CHAIN = 50;
const MAX_PARTICLES = 200;

const HOT_DURATION_MS = 10000;
const HOT_INTERVAL_DROPS = 50;

const TOMBSTONE_RATE_MIN = 0.15;
const TOMBSTONE_RATE_MAX = 0.30;
const TOMBSTONE_RAMP_DROPS = 200;

const POWERUP_KEYS = ['cleanup', 'repair', 'minorCompaction'];
const POWERUP_THRESHOLDS = [1000, 5000, 20000, 50000];
const POWERUP_CAP = 3;

const PERFECT_CLEAR_BONUS = 10000;
const DROP_BASE_SCORE = 5;
const GC_PURGE_SCORE = 50;
const SHADOW_KILL_SCORE = 100;
const TOMBSTONE_COMPACT_SCORE = 500;

const HIGH_SCORE_KEY = 'cassanova.sstableSmasher.highScore';

// ===== Level config (procedural for n >= 4) =====
const LEVEL_PRESET_COLORS = ['#71717a', '#06b6d4', '#8b5cf6', '#10b981'];

function levelConfig(n) {
    if (n < LEVEL_PRESET_COLORS.length) {
        return { color: LEVEL_PRESET_COLORS[n], label: `L${n}`, shimmer: false };
    }
    // 47° rotation is coprime-ish with 360 — adjacent levels stay distinguishable for ~8 steps.
    const k = n - LEVEL_PRESET_COLORS.length;
    const hue = (200 + (k + 1) * 47) % 360;
    const sat = Math.min(70 + k * 3, 85);
    const lig = Math.max(55 - k * 2, 38);
    return { color: `hsl(${hue}, ${sat}%, ${lig}%)`, label: `L${n}`, shimmer: n >= 5 };
}

function compactionScore(newLevel) {
    return 10 * Math.pow(4, newLevel);
}

// ===== Tile factory =====
let _nextTileId = 1;

function makeTile(kind, level = null) {
    return {
        kind,                    // 'sstable' | 'tombstone'
        level: kind === 'sstable' ? level : null,
        turnsLeft: kind === 'tombstone' ? GC_GRACE : null,
        shadowTurns: null,
        shadowVictimId: null,
        compacting: false,
        id: _nextTileId++,
        bornAt: performance.now(),
    };
}

function tileRender(tile) {
    if (tile.kind === 'tombstone') return { color: '#ef4444', label: 'T', shimmer: false };
    return levelConfig(tile.level);
}

// ===== Game =====
class SSTableSmasher {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.width = this.canvas.width = 600;
        this.height = this.canvas.height = 600;
        this.centerX = this.width / 2;
        this.centerY = this.height / 2;

        this.reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        this.highScore = 0;
        this.loadHighScore();
        this.resetState();
        this.isPaused = true;
        this.bindEvents();
    }

    resetState() {
        this.buckets = Array.from({ length: NUM_SECTORS }, () => []);
        this.currentSector = 0;
        this.score = 0;
        this.latency = 0;
        this.dropCount = 0;
        this.isGameOver = false;

        this.currentPiece = this.makeRandomPiece();
        this.nextQueue = [this.makeRandomPiece(), this.makeRandomPiece()];
        this.holdSlot = null;
        this.holdUsedThisTurn = false;

        this.combo = 0;
        this.comboExpiresAt = 0;

        this.powerups = { cleanup: 0, repair: 0, minorCompaction: 0 };
        this.powerupThresholdsHit = new Set();

        this.stuckStrikes = 0;
        this.nextPieceForcedL0 = false;

        this.particles = [];
        this.shake = { magnitude: 0, until: 0 };

        this.hotSector = null;
        this.hotSectorUntil = 0;
        this.nextHotDrop = HOT_INTERVAL_DROPS;

        // Board is empty at reset; suppress immediate perfect-clear bonus.
        this._wasCleared = true;
        this._statusTimer = null;
        this._lastFrame = 0;
        this._lastHudSync = 0;
    }

    // ===== High score persistence =====
    loadHighScore() {
        try {
            const v = parseInt(localStorage.getItem(HIGH_SCORE_KEY) || '0', 10);
            this.highScore = Number.isFinite(v) ? v : 0;
        } catch {
            this.highScore = 0;
        }
    }

    saveHighScore() {
        try {
            localStorage.setItem(HIGH_SCORE_KEY, String(this.highScore));
        } catch { /* quota / incognito — non-fatal */ }
    }

    updateHighScore() {
        if (this.score > this.highScore) {
            this.highScore = this.score;
            this.saveHighScore();
        }
    }

    // ===== Piece generation =====
    tombstoneRate() {
        const t = Math.min(this.dropCount / TOMBSTONE_RAMP_DROPS, 1);
        return TOMBSTONE_RATE_MIN + (TOMBSTONE_RATE_MAX - TOMBSTONE_RATE_MIN) * t;
    }

    makeRandomPiece() {
        if (this.nextPieceForcedL0) {
            this.nextPieceForcedL0 = false;
            return makeTile('sstable', 0);
        }
        return Math.random() < this.tombstoneRate()
            ? makeTile('tombstone')
            : makeTile('sstable', 0);
    }

    // ===== Input =====
    bindEvents() {
        window.addEventListener('keydown', (e) => {
            const modal = document.getElementById('game-modal');
            if (!modal || modal.classList.contains('hidden')) return;
            const manual = document.getElementById('game-manual-overlay');
            if (manual && !manual.classList.contains('hidden')) return;

            const gameKeys = ['Space', 'ArrowLeft', 'ArrowRight', 'KeyH', 'KeyC', 'KeyR', 'KeyM'];
            if (gameKeys.includes(e.code)) e.preventDefault();

            if (this.isPaused || this.isGameOver) {
                if (e.code === 'Space') {
                    const overlay = document.getElementById('game-start-overlay');
                    if (overlay) overlay.classList.add('hidden');
                    this.start();
                }
                return;
            }

            switch (e.code) {
                case 'ArrowLeft':
                    this.currentSector = (this.currentSector - 1 + NUM_SECTORS) % NUM_SECTORS;
                    break;
                case 'ArrowRight':
                    this.currentSector = (this.currentSector + 1) % NUM_SECTORS;
                    break;
                case 'Space':
                    this.dropTable();
                    break;
                case 'KeyH':
                    this.holdSwap();
                    break;
                case 'KeyC':
                    this.usePowerupCleanup();
                    break;
                case 'KeyR':
                    this.usePowerupRepair();
                    break;
                case 'KeyM':
                    this.usePowerupMinorCompaction();
                    break;
            }
            this.syncHUD();
        });
    }

    // ===== Lifecycle =====
    start() {
        this.resetState();
        this.isPaused = false;
        this.syncHUD();
        this.loop();
    }

    endGame() {
        this.isGameOver = true;
        this.updateHighScore();
        this.syncHUD();
    }

    loop() {
        if (this.isPaused) return;
        this.updateParticles();
        const now = performance.now();
        if (now - this._lastHudSync > 150) {
            this.syncHUD();
            this._lastHudSync = now;
        }
        this.draw();
        requestAnimationFrame(() => this.loop());
    }

    // ===== Turn pipeline =====
    dropTable() {
        const bucket = this.buckets[this.currentSector];
        if (bucket.length >= MAX_ROWS) {
            this.endGame();
            return;
        }

        const startOverlay = document.getElementById('game-start-overlay');
        if (startOverlay && !startOverlay.classList.contains('hidden')) {
            startOverlay.classList.add('hidden');
        }

        this.resetComboOnPlayerAction();
        this.processShadowTicks();
        this.processGCGrace();

        const piece = this.currentPiece;
        // Tombstone placed on a non-empty stack starts shadow countdown against
        // the tile directly beneath it. Tracked by tile id so compactions don't
        // accidentally kill the wrong tile.
        if (piece.kind === 'tombstone' && bucket.length > 0) {
            piece.shadowTurns = SHADOW_TURNS;
            piece.shadowVictimId = bucket[bucket.length - 1].id;
        }
        bucket.push(piece);

        this.dropCount++;
        this.checkCompaction(this.currentSector);

        this.currentPiece = this.nextQueue.shift();
        this.nextQueue.push(this.makeRandomPiece());
        this.holdUsedThisTurn = false;

        this.score += DROP_BASE_SCORE;

        this.updateHotEvent();
        this.evaluateStuckHeuristic();
        this.checkPowerupAwards();
        this.checkPerfectClear();
        this.calculateLatency();
        this.updateHighScore();
        this.syncHUD();
    }

    resetComboOnPlayerAction() {
        this.combo = 0;
        this.comboExpiresAt = 0;
    }

    // ===== Tombstone shadow =====
    processShadowTicks() {
        this.buckets.forEach((bucket, sectorIdx) => {
            const kill = new Set();
            for (let i = 0; i < bucket.length; i++) {
                const t = bucket[i];
                if (t.kind !== 'tombstone' || t.shadowTurns === null) continue;
                t.shadowTurns--;
                if (t.shadowTurns > 0) continue;

                const below = i > 0 ? bucket[i - 1] : null;
                if (below && below.id === t.shadowVictimId) {
                    kill.add(i);
                    kill.add(i - 1);
                    this.score += SHADOW_KILL_SCORE;
                    this.emitParticles(sectorIdx, i, '#ef4444', 8);
                } else {
                    // Victim mutated (compacted away). Fizzle silently — do not
                    // let a shadow accidentally delete a freshly-compacted tile.
                    t.shadowTurns = null;
                    t.shadowVictimId = null;
                }
            }
            if (kill.size > 0) {
                this.buckets[sectorIdx] = bucket.filter((_, i) => !kill.has(i));
                this.triggerStatus('SHADOW DELETE', '#ef4444');
                this.checkCompaction(sectorIdx);
            }
        });
    }

    // ===== GC grace (fixes the soft-lock by REMOVING tombstones, not mutating) =====
    processGCGrace() {
        this.buckets.forEach((bucket, sectorIdx) => {
            bucket.forEach(t => {
                if (t.kind === 'tombstone' && t.turnsLeft !== null) t.turnsLeft--;
            });
            let expired = 0;
            const survivors = bucket.filter(t => {
                const done = t.kind === 'tombstone' && t.turnsLeft !== null && t.turnsLeft <= 0;
                if (done) expired++;
                return !done;
            });
            if (expired > 0) {
                this.buckets[sectorIdx] = survivors;
                this.score += GC_PURGE_SCORE * expired;
                this.emitParticlesAtTop(sectorIdx, '#10b981', 5);
                this.triggerStatus('GC GRACE EXPIRED', '#10b981');
                this.checkCompaction(sectorIdx);
            }
        });
    }

    // ===== Compaction =====
    checkCompaction(sectorIdx, depth = 0) {
        if (depth > MAX_CHAIN) return;
        const bucket = this.buckets[sectorIdx];
        if (bucket.length < 4) return;

        // 4 tombstones in a row: remove all (rare, +500, no combo multiplier).
        for (let i = 0; i <= bucket.length - 4; i++) {
            if (bucket.slice(i, i + 4).every(t => t.kind === 'tombstone')) {
                bucket.splice(i, 4);
                this.score += TOMBSTONE_COMPACT_SCORE;
                this.triggerStatus('TOMBSTONE COMPACTION', '#ef4444');
                this.emitParticles(sectorIdx, i, '#ef4444', 12);
                this.scheduleChainStep(sectorIdx, depth);
                return;
            }
        }

        // 4 same-level sstables: compact into level+1.
        for (let i = 0; i <= bucket.length - 4; i++) {
            const head = bucket[i];
            if (head.kind !== 'sstable') continue;
            const level = head.level;
            if (!bucket.slice(i, i + 4).every(t => t.kind === 'sstable' && t.level === level)) continue;

            const merged = makeTile('sstable', level + 1);
            merged.compacting = true;
            bucket.splice(i, 4, merged);
            this.onCompactionResolved(level + 1, sectorIdx, i);
            this.scheduleChainStep(sectorIdx, depth, merged);
            return;
        }
    }

    scheduleChainStep(sectorIdx, depth, mergedTile = null) {
        setTimeout(() => {
            if (this.isPaused || this.isGameOver) return;
            if (mergedTile) mergedTile.compacting = false;
            this.checkCompaction(sectorIdx, depth + 1);
            this.checkPerfectClear();
            this.syncHUD();
        }, CHAIN_DELAY_MS);
    }

    onCompactionResolved(newLevel, sectorIdx, rowIdx) {
        const now = performance.now();
        this.combo = (now < this.comboExpiresAt) ? Math.min(this.combo + 1, COMBO_CAP) : 1;
        this.comboExpiresAt = now + COMBO_WINDOW_MS;

        let pts = compactionScore(newLevel) * this.combo;
        if (this.hotSector === sectorIdx && now < this.hotSectorUntil) pts *= 2;
        this.score += pts;

        const cfg = levelConfig(newLevel);
        const comboSuffix = this.combo > 1 ? ` x${this.combo}` : '';
        this.triggerStatus(`COMPACT ${cfg.label}${comboSuffix}`, '#fbbf24');
        this.emitParticles(sectorIdx, rowIdx, cfg.color, 15);

        if (newLevel >= 4 && !this.reduceMotion) {
            this.shake = { magnitude: 4 + (newLevel - 4) * 1.5, until: now + 250 };
        }
    }

    // ===== Hold =====
    holdSwap() {
        if (this.holdUsedThisTurn) {
            this.triggerStatus('HOLD LOCKED', '#6b7280');
            return;
        }
        const prev = this.holdSlot;
        this.holdSlot = this.currentPiece;
        // Shadow state is placement-time, not piece-intrinsic.
        this.holdSlot.shadowTurns = null;
        this.holdSlot.shadowVictimId = null;
        if (prev) {
            this.currentPiece = prev;
        } else {
            this.currentPiece = this.nextQueue.shift();
            this.nextQueue.push(this.makeRandomPiece());
        }
        this.holdUsedThisTurn = true;
        this.resetComboOnPlayerAction();
    }

    // ===== Power-ups =====
    checkPowerupAwards() {
        POWERUP_THRESHOLDS.forEach((threshold, idx) => {
            if (this.score < threshold || this.powerupThresholdsHit.has(threshold)) return;
            this.powerupThresholdsHit.add(threshold);
            const key = POWERUP_KEYS[idx % POWERUP_KEYS.length];
            if (this.powerups[key] < POWERUP_CAP) {
                this.powerups[key]++;
                this.triggerStatus(`NODETOOL +1 ${key.toUpperCase()}`, '#06b6d4');
            }
        });
    }

    usePowerupCleanup() {
        if (this.powerups.cleanup <= 0) return;
        this.powerups.cleanup--;
        let removed = 0;
        this.buckets.forEach((bucket, sectorIdx) => {
            const before = bucket.length;
            this.buckets[sectorIdx] = bucket.filter(t => t.kind !== 'tombstone');
            const diff = before - this.buckets[sectorIdx].length;
            removed += diff;
            if (diff > 0) {
                this.emitParticlesAtTop(sectorIdx, '#06b6d4', 4);
                this.checkCompaction(sectorIdx);
            }
        });
        this.triggerStatus(`CLEANUP -${removed}T`, '#06b6d4');
        this.resetComboOnPlayerAction();
        this.checkPerfectClear();
    }

    usePowerupRepair() {
        if (this.powerups.repair <= 0) return;
        const bucket = this.buckets[this.currentSector];
        if (bucket.length === 0) {
            this.triggerStatus('NO TARGET', '#6b7280');
            return;
        }
        this.powerups.repair--;
        bucket.pop();
        this.triggerStatus('REPAIR', '#06b6d4');
        this.emitParticlesAtTop(this.currentSector, '#06b6d4', 6);
        this.checkCompaction(this.currentSector);
        this.resetComboOnPlayerAction();
        this.checkPerfectClear();
    }

    usePowerupMinorCompaction() {
        if (this.powerups.minorCompaction <= 0) return;
        const bucket = this.buckets[this.currentSector];
        const found = this.findLowestCompactableRun(bucket);
        if (!found) {
            this.triggerStatus('NO TARGET', '#6b7280');
            return;
        }
        this.powerups.minorCompaction--;
        const merged = makeTile('sstable', found.level + 1);
        merged.compacting = true;
        bucket.splice(found.start, found.len, merged);
        this.onCompactionResolved(found.level + 1, this.currentSector, found.start);
        this.scheduleChainStep(this.currentSector, 0, merged);
        this.resetComboOnPlayerAction();
    }

    findLowestCompactableRun(bucket) {
        let best = null;
        let i = 0;
        while (i < bucket.length) {
            if (bucket[i].kind !== 'sstable') { i++; continue; }
            const level = bucket[i].level;
            let j = i + 1;
            while (j < bucket.length && bucket[j].kind === 'sstable' && bucket[j].level === level) j++;
            const len = j - i;
            if (len >= 2 && (!best || level < best.level)) {
                best = { start: i, len, level };
            }
            i = j;
        }
        return best;
    }

    // ===== Soft-lock safety net =====
    evaluateStuckHeuristic() {
        const sandbagged = this.buckets.filter(b => {
            if (b.length < MAX_ROWS) return false;
            return b.some((t, i) => t.kind === 'tombstone' && i > 0 && i < b.length - 1);
        }).length;
        const hasCompaction = this.buckets.some(b => this.hasPotentialCompaction(b));
        const stuck = sandbagged >= 3 && !hasCompaction;
        if (!stuck) {
            this.stuckStrikes = 0;
            return;
        }
        this.stuckStrikes++;
        if (this.stuckStrikes >= 2) {
            this.stuckStrikes = 0;
            // Force the next piece (queue head) to L0 so the player can breathe.
            if (this.nextQueue[0].kind !== 'sstable' || this.nextQueue[0].level !== 0) {
                this.nextQueue[0] = makeTile('sstable', 0);
            }
            this.triggerStatus('ASSIST: L0 NEXT', '#06b6d4');
        }
    }

    hasPotentialCompaction(bucket) {
        for (let i = 0; i <= bucket.length - 4; i++) {
            const h = bucket[i];
            if (h.kind !== 'sstable') continue;
            if (bucket.slice(i, i + 4).every(t => t.kind === 'sstable' && t.level === h.level)) {
                return true;
            }
        }
        return false;
    }

    // ===== Hot event =====
    updateHotEvent() {
        const now = performance.now();
        if (this.hotSector !== null && now >= this.hotSectorUntil) {
            this.hotSector = null;
        }
        if (this.dropCount >= this.nextHotDrop && this.hotSector === null) {
            this.hotSector = Math.floor(Math.random() * NUM_SECTORS);
            this.hotSectorUntil = now + HOT_DURATION_MS;
            this.nextHotDrop = this.dropCount + HOT_INTERVAL_DROPS;
            this.triggerStatus('READ HOT', '#fbbf24');
        }
    }

    // ===== Perfect clear =====
    checkPerfectClear() {
        const empty = this.buckets.every(b => b.length === 0);
        if (empty && !this._wasCleared) {
            this.score += PERFECT_CLEAR_BONUS;
            this.triggerStatus(`CLUSTER STABLE +${PERFECT_CLEAR_BONUS}`, '#fbbf24');
            this.emitPerfectClearParticles();
            this.updateHighScore();
        }
        this._wasCleared = empty;
    }

    // ===== Latency =====
    calculateLatency() {
        let load = 0;
        this.buckets.forEach(b => b.forEach(t => {
            load += t.kind === 'tombstone' ? 5 : 1;
        }));
        this.latency = Math.round((load / (NUM_SECTORS * MAX_ROWS)) * 100);
    }

    // ===== Status line =====
    triggerStatus(text, color) {
        const el = document.getElementById('game-disk-status');
        if (!el) return;
        el.textContent = text;
        el.style.color = color;
        clearTimeout(this._statusTimer);
        this._statusTimer = setTimeout(() => {
            el.textContent = 'NOMINAL';
            el.style.color = 'var(--color-success)';
        }, 900);
    }

    // ===== Particles =====
    emitParticles(sectorIdx, rowIdx, color, count) {
        const angle = ((sectorIdx + 0.5) / NUM_SECTORS) * Math.PI * 2;
        const dist = INNER_RADIUS + rowIdx * ROW_HEIGHT;
        const x = this.centerX + Math.cos(angle) * dist;
        const y = this.centerY + Math.sin(angle) * dist;
        for (let i = 0; i < count; i++) {
            const theta = Math.random() * Math.PI * 2;
            const speed = 60 + Math.random() * 120;
            this.particles.push({
                x, y,
                vx: Math.cos(theta) * speed,
                vy: Math.sin(theta) * speed,
                life: 0.6 + Math.random() * 0.4,
                maxLife: 1,
                color,
                size: 2 + Math.random() * 2,
            });
        }
        this.trimParticles();
    }

    emitParticlesAtTop(sectorIdx, color, count) {
        const rIdx = this.buckets[sectorIdx].length;
        this.emitParticles(sectorIdx, rIdx, color, count);
    }

    emitPerfectClearParticles() {
        for (let i = 0; i < 80; i++) {
            const theta = Math.random() * Math.PI * 2;
            const speed = 80 + Math.random() * 180;
            this.particles.push({
                x: this.centerX,
                y: this.centerY,
                vx: Math.cos(theta) * speed,
                vy: Math.sin(theta) * speed,
                life: 1.2 + Math.random() * 0.5,
                maxLife: 1.5,
                color: '#fbbf24',
                size: 2 + Math.random() * 3,
            });
        }
        this.trimParticles();
    }

    trimParticles() {
        while (this.particles.length > MAX_PARTICLES) this.particles.shift();
    }

    updateParticles() {
        const now = performance.now();
        if (!this._lastFrame) { this._lastFrame = now; return; }
        // Clamp dt so tab-switch blurs don't teleport particles across the ring.
        const dt = Math.min((now - this._lastFrame) / 1000, 0.033);
        this._lastFrame = now;
        for (const p of this.particles) {
            p.x += p.vx * dt;
            p.y += p.vy * dt;
            p.life -= dt;
        }
        this.particles = this.particles.filter(p => p.life > 0);
    }

    // ===== Rendering =====
    draw() {
        const ctx = this.ctx;
        ctx.save();
        ctx.clearRect(0, 0, this.width, this.height);

        const now = performance.now();
        if (this.shake.until > now && !this.reduceMotion) {
            const m = this.shake.magnitude;
            ctx.translate((Math.random() - 0.5) * m * 2, (Math.random() - 0.5) * m * 2);
        }

        this.drawRing();
        this.drawHotSector(now);
        this.buckets.forEach((bucket, sIdx) => {
            const baseAngle = ((sIdx + 0.5) / NUM_SECTORS) * Math.PI * 2;
            bucket.forEach((tile, rIdx) => this.drawTile(tile, baseAngle, rIdx));
        });
        this.drawSelection();
        this.drawParticles();

        if (this.isGameOver) this.drawGameOver();
        ctx.restore();
    }

    drawRing() {
        const ctx = this.ctx;
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        ctx.setLineDash([]);
        ctx.lineWidth = 1;
        for (let i = 0; i < NUM_SECTORS; i++) {
            const a = (i / NUM_SECTORS) * Math.PI * 2;
            ctx.beginPath();
            ctx.moveTo(this.centerX, this.centerY);
            ctx.lineTo(this.centerX + Math.cos(a) * 300, this.centerY + Math.sin(a) * 300);
            ctx.stroke();
        }
    }

    drawHotSector(now) {
        if (this.hotSector === null || now >= this.hotSectorUntil) return;
        const ctx = this.ctx;
        const a0 = (this.hotSector / NUM_SECTORS) * Math.PI * 2;
        const a1 = ((this.hotSector + 1) / NUM_SECTORS) * Math.PI * 2;
        const pulse = 0.04 + 0.03 * Math.sin(now / 200);
        ctx.fillStyle = `rgba(251, 191, 36, ${pulse})`;
        ctx.beginPath();
        ctx.moveTo(this.centerX, this.centerY);
        ctx.arc(this.centerX, this.centerY, 300, a0, a1);
        ctx.closePath();
        ctx.fill();
    }

    drawTile(tile, baseAngle, rIdx) {
        const ctx = this.ctx;
        const dist = INNER_RADIUS + rIdx * ROW_HEIGHT;
        const x = this.centerX + Math.cos(baseAngle) * dist;
        const y = this.centerY + Math.sin(baseAngle) * dist;
        const render = tileRender(tile);

        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(baseAngle);

        ctx.fillStyle = render.color;
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = tile.compacting ? 2 : 0.5;
        if (tile.compacting) {
            ctx.shadowBlur = 15;
            ctx.shadowColor = render.color;
        }
        ctx.fillRect(-BLOCK_SIZE / 2, -BLOCK_SIZE / 2, BLOCK_SIZE, BLOCK_SIZE);
        ctx.strokeRect(-BLOCK_SIZE / 2, -BLOCK_SIZE / 2, BLOCK_SIZE, BLOCK_SIZE);

        // Cheap shimmer: a random highlight pixel, 20% of frames.
        if (render.shimmer && !this.reduceMotion) {
            const frame = Math.floor(performance.now() / 80);
            if ((frame + tile.id) % 5 === 0) {
                ctx.fillStyle = 'rgba(255, 255, 255, 0.75)';
                const sx = (Math.random() - 0.5) * (BLOCK_SIZE - 4);
                const sy = (Math.random() - 0.5) * (BLOCK_SIZE - 4);
                ctx.fillRect(sx, sy, 2, 2);
            }
        }

        ctx.shadowBlur = 0;
        ctx.fillStyle = '#fff';
        ctx.font = '800 10px "JetBrains Mono", monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(render.label, 0, 0);

        if (tile.kind === 'tombstone') {
            ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
            ctx.font = '700 7px "JetBrains Mono", monospace';
            ctx.textAlign = 'right';
            ctx.fillText(String(tile.turnsLeft), 7, 7);
            if (tile.shadowTurns !== null) {
                ctx.fillStyle = '#fbbf24';
                ctx.textAlign = 'left';
                ctx.fillText(`s${tile.shadowTurns}`, -8, 7);
            }
        }
        ctx.restore();
    }

    drawSelection() {
        const ctx = this.ctx;
        const activeAngle = ((this.currentSector + 0.5) / NUM_SECTORS) * Math.PI * 2;
        ctx.strokeStyle = '#1287b1';
        ctx.setLineDash([5, 2]);
        ctx.lineWidth = 1;
        const bucketLen = this.buckets[this.currentSector].length;
        ctx.beginPath();
        ctx.arc(this.centerX, this.centerY, INNER_RADIUS + bucketLen * ROW_HEIGHT,
                activeAngle - 0.2, activeAngle + 0.2);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.moveTo(this.centerX, this.centerY);
        ctx.lineTo(this.centerX + Math.cos(activeAngle) * 50, this.centerY + Math.sin(activeAngle) * 50);
        ctx.stroke();
    }

    drawParticles() {
        const ctx = this.ctx;
        ctx.save();
        ctx.globalCompositeOperation = 'lighter';
        for (const p of this.particles) {
            const alpha = Math.max(0, Math.min(1, p.life / p.maxLife));
            ctx.globalAlpha = alpha;
            ctx.fillStyle = p.color;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.restore();
    }

    drawGameOver() {
        const ctx = this.ctx;
        ctx.fillStyle = 'rgba(0,0,0,0.8)';
        ctx.fillRect(0, 0, this.width, this.height);
        ctx.textAlign = 'center';
        ctx.fillStyle = '#fff';
        ctx.font = '800 32px "JetBrains Mono", monospace';
        ctx.fillText('NODE CRASHED', this.centerX, this.centerY - 36);
        ctx.font = '14px "JetBrains Mono", monospace';
        ctx.fillStyle = '#a1a1aa';
        ctx.fillText('BLOOM FILTER OVERLOAD / DISK FULL', this.centerX, this.centerY - 4);
        ctx.fillStyle = '#fff';
        ctx.fillText(`FINAL  ${this.score}`, this.centerX, this.centerY + 28);
        ctx.fillStyle = '#1287b1';
        ctx.fillText(`BEST  ${this.highScore}`, this.centerX, this.centerY + 50);
        ctx.fillStyle = '#a1a1aa';
        ctx.fillText('SPACE TO REBOOT', this.centerX, this.centerY + 86);
    }

    // ===== HUD sync (DOM) =====
    syncHUD() {
        const $ = id => document.getElementById(id);

        const scoreEl = $('game-score-val');
        if (scoreEl) scoreEl.textContent = this.score;
        const latEl = $('latency-val');
        if (latEl) {
            latEl.textContent = this.latency + 'ms';
            latEl.style.color = this.latency > 60 ? '#ef4444'
                : (this.latency > 30 ? '#fbbf24' : '#10b981');
        }
        const bestEl = $('game-best-val');
        if (bestEl) bestEl.textContent = this.highScore;

        this.nextQueue.forEach((tile, i) => {
            const el = $(`game-next-${i}`);
            if (el) this.styleMiniTile(el, tile);
        });

        const curEl = $('game-current');
        if (curEl) this.styleMiniTile(curEl, this.currentPiece);

        const holdEl = $('game-hold');
        if (holdEl) this.styleMiniTile(holdEl, this.holdSlot);

        POWERUP_KEYS.forEach(key => {
            const countEl = $(`powerup-${key}`);
            if (!countEl) return;
            const count = this.powerups[key];
            countEl.textContent = count;
            const badge = countEl.closest('.powerup-badge');
            if (badge) badge.classList.toggle('available', count > 0);
        });

        const comboEl = $('combo-counter');
        if (comboEl) {
            const active = this.combo >= 2 && performance.now() < this.comboExpiresAt;
            if (active) {
                comboEl.textContent = `CHAIN x${this.combo}`;
                comboEl.classList.add('active');
            } else {
                comboEl.classList.remove('active');
            }
        }
    }

    styleMiniTile(el, tile) {
        if (!tile) {
            el.textContent = '--';
            el.style.background = 'transparent';
            el.style.color = 'var(--text-muted)';
            el.style.borderColor = '';
            return;
        }
        const r = tileRender(tile);
        el.textContent = r.label;
        el.style.background = r.color;
        el.style.color = '#fff';
        el.style.borderColor = r.color;
    }
}

// ===== Bootstrap =====
window.initGame = () => {
    const game = new SSTableSmasher('game-canvas');
    window.gameInstance = game;
    game.syncHUD();

    // Back-compat shim for any external callers of the old API.
    window.updateGameScore = (score, latency) => {
        const scoreEl = document.getElementById('game-score-val');
        if (scoreEl) scoreEl.textContent = score;
        const latEl = document.getElementById('latency-val');
        if (latEl) {
            latEl.textContent = latency + 'ms';
            latEl.style.color = latency > 60 ? '#ef4444'
                : (latency > 30 ? '#fbbf24' : '#10b981');
        }
    };
};
