const ConfirmModal = {
    modal: null,
    title: null,
    body: null,
    confirmBtn: null,
    cancelBtn: null,
    callback: null,

    init() {
        if (this.modal) return;

        // Create modal element if it doesn't exist
        const modalHtml = `
            <div id="global-confirm-modal" class="modal hidden">
                <div class="modal-content glass-panel">
                    <div class="modal-header">
                        <h3 id="confirm-modal-title">Confirm Action</h3>
                        <span class="modal-close" id="confirm-modal-close">&times;</span>
                    </div>
                    <div class="modal-body" id="confirm-modal-body">
                        Are you sure you want to proceed?
                    </div>
                    <div class="modal-footer">
                        <button class="btn-secondary" id="confirm-modal-cancel">Cancel</button>
                        <button class="btn-primary" id="confirm-modal-ok">Confirm</button>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        this.modal = document.getElementById('global-confirm-modal');
        this.title = document.getElementById('confirm-modal-title');
        this.body = document.getElementById('confirm-modal-body');
        this.confirmBtn = document.getElementById('confirm-modal-ok');
        this.cancelBtn = document.getElementById('confirm-modal-cancel');
        this.closeX = document.getElementById('confirm-modal-close');

        const close = () => this.modal.classList.add('hidden');

        this.cancelBtn.onclick = close;
        this.closeX.onclick = close;
        this.modal.onclick = (e) => { if (e.target === this.modal) close(); };

        this.confirmBtn.onclick = () => {
            if (this.callback) this.callback();
            close();
        };
    },

    show(options) {
        this.init();
        const { title, body, confirmText, confirmClass, onConfirm } = options;

        this.title.textContent = title || 'Confirm Action';
        this.body.innerHTML = body || 'Are you sure?';
        this.confirmBtn.textContent = confirmText || 'Confirm';

        // Reset and apply classes
        this.confirmBtn.className = 'btn-primary';
        if (confirmClass) this.confirmBtn.classList.add(confirmClass);

        this.callback = onConfirm;
        this.modal.classList.remove('hidden');
    }
};

window.ConfirmModal = ConfirmModal;
