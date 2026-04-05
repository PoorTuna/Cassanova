/**
 * Searchable combobox — replaces <select> with a filterable dropdown.
 *
 * HTML structure expected:
 *   <div class="combobox" data-id="my-id" data-selected="">
 *       <input class="combobox-input" type="text" />
 *       <div class="combobox-list hidden">
 *           <div class="combobox-option" data-value="val">Label</div>
 *       </div>
 *   </div>
 *
 * Call initComboboxes(container) to activate all .combobox elements within container.
 */

function initComboboxes(container) {
    if (!container) return;
    container.querySelectorAll('.combobox').forEach(box => {
        const input = box.querySelector('.combobox-input');
        const list = box.querySelector('.combobox-list');
        const options = list.querySelectorAll('.combobox-option');

        input.addEventListener('focus', () => {
            list.classList.remove('hidden');
            filterOptions('');
        });

        input.addEventListener('input', () => {
            list.classList.remove('hidden');
            filterOptions(input.value.toLowerCase());
        });

        options.forEach(opt => {
            opt.addEventListener('mousedown', (e) => {
                e.preventDefault();
                input.value = opt.dataset.value;
                box.dataset.selected = opt.dataset.value;
                list.classList.add('hidden');
            });
        });

        input.addEventListener('blur', () => {
            setTimeout(() => list.classList.add('hidden'), 150);
        });

        function filterOptions(q) {
            options.forEach(opt => {
                opt.style.display = opt.dataset.value.toLowerCase().includes(q) ? '' : 'none';
            });
        }
    });
}
