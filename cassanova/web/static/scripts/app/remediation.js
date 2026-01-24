const STATES = ['pending-approval', 'approved', 'tainted', 'finalizers-removed', 'k8ssandra-task-scheduled', 'completed'];
const ACTIVE_STATES = ['approved', 'tainted', 'finalizers-removed', 'k8ssandra-task-scheduled'];
const HISTORY_STATES = ['completed', 'failed', 'cancelled'];

let currentUser = 'admin';
let selectedRemediationId = null;

async function fetchRemediationStatus() {
    try {
        const response = await fetch('/api/v1/remediation/status');
        if (!response.ok) {
            throw new Error('Failed to fetch remediation status');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching remediation status:', error);
        return { jobs: [], pending_approval: 0, active: 0, completed: 0, failed: 0 };
    }
}

function getProgress(state) {
    const index = STATES.indexOf(state);
    if (index === -1) return 0;
    return Math.round((index / (STATES.length - 1)) * 100);
}

function formatTime(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleString();
}

function renderRemediationCard(job, showActions = true) {
    const progress = getProgress(job.state);

    return `
        <div class="remediation-card" data-id="${job.id}">
            <div class="remediation-card-header">
                <span class="remediation-id">${job.id}</span>
                <span class="remediation-state ${job.state}">${job.state.replace(/-/g, ' ')}</span>
            </div>
            <div class="remediation-info">
                <div class="info-item">
                    <span class="info-label">Node</span>
                    <span class="info-value">${job.node_name}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Cluster</span>
                    <span class="info-value">${job.cluster_name || '-'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Pod</span>
                    <span class="info-value">${job.pod_name}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Datacenter</span>
                    <span class="info-value">${job.datacenter || '-'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Detected</span>
                    <span class="info-value">${formatTime(job.detected_at)}</span>
                </div>
                ${job.error ? `
                <div class="info-item">
                    <span class="info-label">Error</span>
                    <span class="info-value" style="color: var(--color-failed)">${job.error}</span>
                </div>
                ` : ''}
            </div>
            ${ACTIVE_STATES.includes(job.state) ? `
            <div class="remediation-progress">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress}%"></div>
                </div>
            </div>
            ` : ''}
            ${showActions && job.state === 'pending-approval' ? `
            <div class="remediation-actions">
                <button class="btn btn-approve" onclick="openApproveModal('${job.id}', '${job.node_name}', '${job.cluster_name}', '${job.pod_name}')">Approve</button>
                <button class="btn btn-cancel" onclick="cancelRemediation('${job.id}')">Dismiss</button>
            </div>
            ` : ''}
            ${showActions && ACTIVE_STATES.includes(job.state) ? `
            <div class="remediation-actions">
                <button class="btn btn-cancel" onclick="cancelRemediation('${job.id}')">Cancel</button>
            </div>
            ` : ''}
        </div>
    `;
}

function updateDashboard(data) {
    document.getElementById('stat-pending').textContent = data.pending_approval || 0;
    document.getElementById('stat-active').textContent = data.active || 0;
    document.getElementById('stat-completed').textContent = data.completed || 0;
    document.getElementById('stat-failed').textContent = data.failed || 0;

    const pendingJobs = data.jobs.filter(j => j.state === 'pending-approval');
    const activeJobs = data.jobs.filter(j => ACTIVE_STATES.includes(j.state));
    const historyJobs = data.jobs.filter(j => HISTORY_STATES.includes(j.state));

    const pendingList = document.getElementById('pending-list');
    if (pendingJobs.length > 0) {
        pendingList.innerHTML = pendingJobs.map(j => renderRemediationCard(j)).join('');
    } else {
        pendingList.innerHTML = '<div class="empty-state">No pending recoveries</div>';
    }

    const activeList = document.getElementById('active-list');
    if (activeJobs.length > 0) {
        activeList.innerHTML = activeJobs.map(j => renderRemediationCard(j)).join('');
    } else {
        activeList.innerHTML = '<div class="empty-state">No active recoveries</div>';
    }

    const historyList = document.getElementById('history-list');
    if (historyJobs.length > 0) {
        historyList.innerHTML = historyJobs.map(j => renderRemediationCard(j, false)).join('');
    } else {
        historyList.innerHTML = '<div class="empty-state">No recovery history</div>';
    }
}

function openApproveModal(id, nodeName, clusterName, podName) {
    selectedRemediationId = id;
    document.getElementById('modal-node').textContent = nodeName;
    document.getElementById('modal-cluster').textContent = clusterName || '-';
    document.getElementById('modal-pod').textContent = podName;
    document.getElementById('approve-modal').classList.remove('hidden');
}

function closeApproveModal() {
    selectedRemediationId = null;
    document.getElementById('approve-modal').classList.add('hidden');
}

async function confirmApprove() {
    if (!selectedRemediationId) return;

    try {
        const response = await fetch('/api/v1/remediation/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                remediation_id: selectedRemediationId,
                approved_by: currentUser
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to approve');
        }

        closeApproveModal();
        await refreshDashboard();
        Toast.success('Recovery approved successfully');

    } catch (error) {
        console.error('Error approving remediation:', error);
        Toast.error('Failed to approve recovery: ' + error.message);
    }
}

function openCancelModal(id) {
    selectedRemediationId = id;
    document.getElementById('cancel-modal').classList.remove('hidden');
}

function closeCancelModal() {
    selectedRemediationId = null;
    document.getElementById('cancel-modal').classList.add('hidden');
}

const cancelRemediation = openCancelModal;

async function confirmCancel() {
    if (!selectedRemediationId) return;

    try {
        const response = await fetch(`/api/v1/remediation/cancel/${selectedRemediationId}`, {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to cancel');
        }

        closeCancelModal();
        await refreshDashboard();
        Toast.success('Recovery cancelled');

    } catch (error) {
        console.error('Error cancelling remediation:', error);
        Toast.error('Failed to cancel: ' + error.message);
    }
}

async function triggerScan() {
    const btn = document.getElementById('scan-now-btn');
    btn.disabled = true;
    const originalHtml = btn.innerHTML;

    try {
        const response = await fetch('/api/v1/remediation/scan', {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Scan failed');
        }

        await refreshDashboard();
        Toast.success('Scan completed successfully');

    } catch (error) {
        console.error('Error triggering scan:', error);
        Toast.error('Failed to trigger scan: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
    }
}



async function refreshDashboard() {
    const data = await fetchRemediationStatus();
    updateDashboard(data);
}

document.addEventListener('DOMContentLoaded', () => {
    refreshDashboard();
    setInterval(refreshDashboard, 5000);

    document.getElementById('confirm-approve-btn').addEventListener('click', confirmApprove);
    document.getElementById('confirm-cancel-btn').addEventListener('click', confirmCancel);

    document.getElementById('approve-modal').addEventListener('click', (e) => {
        if (e.target.id === 'approve-modal') {
            closeApproveModal();
        }
    });

    document.getElementById('cancel-modal').addEventListener('click', (e) => {
        if (e.target.id === 'cancel-modal') {
            closeCancelModal();
        }
    });
});
