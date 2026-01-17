document.addEventListener('DOMContentLoaded', () => {
    const explorer = document.querySelector('.explorer-page');
    const cluster = explorer.dataset.cluster;
    const keyspace = explorer.dataset.keyspace;
    const table = explorer.dataset.table;
    const pkCols = JSON.parse(explorer.dataset.pk);

    const tableHead = document.getElementById('table-head-row');
    const tableBody = document.getElementById('table-body');
    const loadingOverlay = document.getElementById('loading-overlay');
    const rowCountLabel = document.getElementById('row-count');
    const prevPageBtn = document.getElementById('prev-page');
    const nextPageBtn = document.getElementById('next-page');

    const addFilterBtn = document.getElementById('add-filter-btn');
    const filterPopover = document.getElementById('filter-popover');
    const cancelFilterBtn = document.getElementById('cancel-filter');
    const colSelect = document.getElementById('filter-column-select');
    const opSelect = document.getElementById('filter-operator-select');
    const valInput = document.getElementById('filter-value-input');
    const allowFilteringToggle = document.getElementById('allow-filtering-toggle');
    const submitFilterBtn = document.getElementById('submit-filter');
    const chipsContainer = document.getElementById('filter-chips');
    const insertRowBtn = document.getElementById('insert-row-btn');
    const insertRowModal = document.getElementById('insert-row-modal');
    const insertFormFields = document.getElementById('insert-form-fields');
    const insertForm = document.getElementById('insert-row-form');
    const submitInsertBtn = document.getElementById('submit-insert-btn');
    const deleteConfirmModal = document.getElementById('delete-confirm-modal');
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    const deleteRowDetails = document.getElementById('delete-row-details');

    let currentData = [];
    let pagingStack = [null];
    let nextPagingState = null;
    let activeFilters = []; // Array of objects { col, op, val }
    let explicitAllowFiltering = false;
    let tableSchema = null;
    let deletingRowIndex = -1;
    let isFetching = false;

    async function fetchData(dir = 'next') {
        if (isFetching && dir === 'next' && !nextPagingState) return;
        isFetching = true;

        loadingOverlay.classList.remove('hidden');
        if (dir !== 'next' || !nextPagingState) {
            // New query or refresh, clear previous data
            tableBody.innerHTML = '';
        }

        let stateToUse = null;
        if (dir === 'next') {
            stateToUse = nextPagingState;
        } else if (dir === 'prev') {
            pagingStack.pop();
            stateToUse = pagingStack[pagingStack.length - 1];
        }

        const url = new URL(`/api/v1/cluster/${cluster}/keyspace/${keyspace}/table/${table}/data`, window.location.origin);
        if (activeFilters.length > 0) {
            url.searchParams.set('filter_json', JSON.stringify(activeFilters));
        }
        if (explicitAllowFiltering) {
            url.searchParams.set('allow_filtering', 'true');
        }
        if (stateToUse) url.searchParams.set('paging_state', stateToUse);

        try {
            const response = await fetch(url);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || `Server error: ${response.status}`);
            }

            if (data.rows && data.rows.length > 0) {
                currentData = data.rows;
                nextPagingState = data.next_paging_state;
                if (dir === 'next' && stateToUse) {
                    pagingStack.push(stateToUse);
                }
                renderTable(data.rows);

                // Populate column selector if empty
                if (colSelect.options.length <= 1) {
                    populateColumnSelector(Object.keys(data.rows[0]));
                }

                // Only show expensive query warning if ALLOW FILTERING is explicitly enabled
                if (explicitAllowFiltering) {
                    showExpensiveQueryWarning();
                } else {
                    hideExpensiveQueryWarning();
                }
            } else {
                // No rows returned
                if (dir === 'next' && pagingStack.length > 1 && stateToUse) {
                    // We shouldn't have advanced to this empty page
                    Toast.info("No more results available.");
                    nextPagingState = null; // Kill the dead-end state
                } else {
                    renderTable([]); // Show "No data found"
                    nextPagingState = null;
                }
            }

            updatePaginationUI();
        } catch (error) {
            console.error('Error fetching data:', error);
            tableBody.innerHTML = `<tr><td colspan="100" style="text-align:center; padding: 40px;">
                <div style="color: var(--color-danger); font-weight: 600; margin-bottom: 8px;">Failed to Load Data</div>
                <div style="color: var(--text-muted); font-size: 0.9rem;">${error.message}</div>
            </td></tr>`;
        } finally {
            loadingOverlay.classList.add('hidden');
            isFetching = false;
        }
    }

    function populateColumnSelector(cols) {
        cols.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c;
            opt.textContent = c;
            colSelect.appendChild(opt);
        });
    }

    function renderChips() {
        chipsContainer.innerHTML = activeFilters.map((f, i) => `
            <div class="filter-chip" title="Double-click to edit">
                <strong>${f.col}</strong> <span class="op">${f.op}</span> ${f.val}
                <span class="remove-filter" data-index="${i}">×</span>
            </div>
        `).join('');

        // Add explicit allow filtering chip if enabled
        if (explicitAllowFiltering) {
            const chip = document.createElement('div');
            chip.className = 'filter-chip filtering-enabled';
            chip.innerHTML = `<strong>ALLOW FILTERING</strong> <span class="remove-filtering-flag">×</span>`;
            chip.querySelector('.remove-filtering-flag').onclick = () => {
                explicitAllowFiltering = false;
                allowFilteringToggle.checked = false;
                refreshAndFetch();
            };
            chipsContainer.appendChild(chip);
        }

        chipsContainer.querySelectorAll('.filter-chip').forEach(chip => {
            const idx = parseInt(chip.querySelector('.remove-filter').dataset.index);
            chip.addEventListener('dblclick', (e) => {
                if (e.target.classList.contains('remove-filter')) return;
                startEditingFilter(idx);
            });

            const removeBtn = chip.querySelector('.remove-filter');
            removeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                activeFilters.splice(idx, 1);
                refreshAndFetch();
            });
        });
    }

    function startEditingFilter(index) {
        const f = activeFilters[index];
        editingFilterIndex = index;
        colSelect.value = f.col;
        opSelect.value = f.op;
        valInput.value = f.val;

        filterPopover.classList.remove('hidden');
        submitFilterBtn.textContent = 'Update Filter';
        valInput.focus();
    }

    function refreshAndFetch() {
        renderChips();
        pagingStack = [null];
        nextPagingState = null;
        fetchData();
    }

    addFilterBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        filterPopover.classList.toggle('hidden');
        if (!filterPopover.classList.contains('hidden')) {
            valInput.focus();
        }
    });

    cancelFilterBtn.addEventListener('click', () => {
        filterPopover.classList.add('hidden');
        editingFilterIndex = -1;
        submitFilterBtn.textContent = 'Add Filter';
    });

    submitFilterBtn.addEventListener('click', () => {
        const col = colSelect.value;
        const op = opSelect.value;
        const val = valInput.value.trim();

        const oldAllow = explicitAllowFiltering;
        explicitAllowFiltering = allowFilteringToggle.checked;

        let changed = (oldAllow !== explicitAllowFiltering);

        if (col && op && val) {
            if (editingFilterIndex > -1) {
                activeFilters[editingFilterIndex] = { col, op, val };
                editingFilterIndex = -1;
            } else {
                activeFilters.push({ col, op, val });
            }
            changed = true;
            submitFilterBtn.textContent = 'Add Filter';
            valInput.value = '';
        }

        if (changed) {
            filterPopover.classList.add('hidden');
            refreshAndFetch();
        } else if (col || val) {
            // User typed something but missed a field
            Toast.info("Please select a column, operator, and provide a value.");
        } else {
            // Nothing changed, just close
            filterPopover.classList.add('hidden');
        }
    });

    valInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') submitFilterBtn.click();
    });

    // Close popover on click outside
    document.addEventListener('click', (e) => {
        if (!filterPopover.contains(e.target) && e.target !== addFilterBtn) {
            filterPopover.classList.add('hidden');
        }
    });

    function updatePaginationUI() {
        prevPageBtn.disabled = pagingStack.length <= 1;
        nextPageBtn.disabled = !nextPagingState;

        const pageNum = pagingStack.length;
        const pageInfo = document.getElementById('page-info');
        if (pageInfo) {
            pageInfo.textContent = `Page ${pageNum} ${nextPagingState ? '(more results available)' : '(end of data)'}`;
        }
    }

    function showExpensiveQueryWarning() {
        document.getElementById('expensive-query-warning').classList.remove('hidden');
    }

    function hideExpensiveQueryWarning() {
        document.getElementById('expensive-query-warning').classList.add('hidden');
    }

    function renderTable(data) {
        if (!data || data.length === 0) {
            tableHead.innerHTML = '';
            tableBody.innerHTML = '<tr><td colspan="100" style="text-align:center">No data found</td></tr>';
            rowCountLabel.textContent = '0 rows';
            return;
        }

        // Generate Headers
        const cols = Object.keys(data[0]);
        tableHead.innerHTML = cols.map(col => `
            <th class="${pkCols.includes(col) ? 'pk-col' : ''}">
                ${col}
                ${pkCols.includes(col) ? ' 🔑' : ''}
            </th>
        `).join('') + '<th class="actions-head">Actions</th>';

        // Generate Rows
        tableBody.innerHTML = data.map((row, index) => `
            <tr data-index="${index}">
                ${cols.map(col => {
            const isPK = pkCols.includes(col);
            return `
                    <td data-col="${col}" class="${isPK ? 'pk-col read-only' : 'editable-cell'}" title="${isPK ? 'Primary Key (Read-only)' : row[col]}">
                        ${formatCell(row[col])}
                        ${!isPK ? '<span class="edit-hint">✎</span>' : ''}
                    </td>
                `}).join('')}
                <td class="actions-cell">
                    <button class="btn-icon-danger delete-row-btn" title="Delete Row">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"></path>
                        </svg>
                    </button>
                </td>
            </tr>
        `).join('');

        rowCountLabel.textContent = `${data.length} rows`;
        attachCellEvents();
    }

    function formatCell(val) {
        if (val === null) return '<span class="syntax-null">null</span>';
        if (typeof val === 'object') return JSON.stringify(val);
        return val;
    }

    function attachCellEvents() {
        const cells = tableBody.querySelectorAll('td');
        cells.forEach(cell => {
            if (!cell.classList.contains('actions-cell')) {
                cell.addEventListener('dblclick', () => startEditing(cell));
                cell.addEventListener('contextmenu', (e) => showContextMenu(e, cell));
            }
        });

        // Add events for delete buttons
        tableBody.querySelectorAll('.delete-row-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const rowIndex = btn.closest('tr').dataset.index;
                confirmDeletion(rowIndex);
            });
        });
    }

    const contextMenu = document.getElementById('context-menu');
    const metaDetails = document.getElementById('metadata-details');
    let activeCell = null;

    function showContextMenu(e, cell) {
        e.preventDefault();
        activeCell = cell;

        contextMenu.classList.remove('hidden');
        contextMenu.style.left = `${e.pageX}px`;
        contextMenu.style.top = `${e.pageY}px`;
        metaDetails.classList.add('hidden'); // Reset for new cell

        // Handle clicks outside
        const closeMenu = (ev) => {
            if (!contextMenu.contains(ev.target)) {
                contextMenu.classList.add('hidden');
                document.removeEventListener('click', closeMenu);
            }
        };
        setTimeout(() => document.addEventListener('click', closeMenu), 0);
    }

    document.getElementById('menu-metadata').addEventListener('click', async (e) => {
        e.stopPropagation();
        if (!activeCell) return;

        const col = activeCell.dataset.col;
        const rowIndex = activeCell.parentElement.dataset.index;
        const rowData = currentData[rowIndex];

        const pk = {};
        pkCols.forEach(p => pk[p] = rowData[p]);

        metaDetails.classList.remove('hidden');
        document.getElementById('meta-ttl').textContent = 'Loading...';
        document.getElementById('meta-writetime').textContent = 'Loading...';

        try {
            const url = `/api/v1/cluster/${cluster}/keyspace/${keyspace}/table/${table}/cell-metadata?pk=${encodeURIComponent(JSON.stringify(pk))}&column=${col}`;
            const response = await fetch(url);
            const data = await response.json();

            document.getElementById('meta-ttl').textContent = data.ttl !== null ? `${data.ttl}s` : 'N/A';
            document.getElementById('meta-writetime').textContent = data.writetime || 'N/A';
        } catch (error) {
            console.error('Meta fetch error:', error);
            metaDetails.classList.add('hidden');
        }
    });

    document.getElementById('menu-copy-cql').addEventListener('click', () => {
        if (!activeCell) return;
        const col = activeCell.dataset.col;
        const rowIndex = activeCell.parentElement.dataset.index;
        const rowData = currentData[rowIndex];
        const val = rowData[col];

        const pk = {};
        pkCols.forEach(p => pk[p] = rowData[p]);

        const where = Object.entries(pk).map(([k, v]) => `${k} = ${formatValue(v)}`).join(' AND ');
        const cql = `UPDATE ${keyspace}.${table} SET ${col} = ${formatValue(val)} WHERE ${where};`;

        navigator.clipboard.writeText(cql).then(() => {
            Toast.success('CQL copied to clipboard!');
            contextMenu.classList.add('hidden');
        });
    });

    function formatValue(v) {
        if (typeof v === 'string') return `'${v}'`;
        if (v === null) return 'null';
        return v;
    }

    function startEditing(cell) {
        if (cell.classList.contains('read-only')) return;
        if (cell.querySelector('.cell-editor')) return;

        const col = cell.dataset.col;
        const rowIndex = cell.parentElement.dataset.index;
        const originalValue = currentData[rowIndex][col];

        const input = document.createElement('input');
        input.className = 'cell-editor';
        input.value = originalValue === null ? '' : originalValue;

        cell.appendChild(input);
        input.focus();

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                saveEdit(cell, input.value);
            } else if (e.key === 'Escape') {
                cancelEdit(cell, originalValue);
            }
        });

        input.addEventListener('blur', () => {
            cancelEdit(cell, originalValue);
        });
    }

    async function saveEdit(cell, newValue) {
        const col = cell.dataset.col;
        const rowIndex = cell.parentElement.dataset.index;
        const rowData = currentData[rowIndex];

        // Prepare PK for update
        const pk = {};
        pkCols.forEach(p => pk[p] = rowData[p]);

        const updates = {};
        updates[col] = newValue;

        // Visual feedback
        cell.style.opacity = '0.5';

        try {
            const response = await fetch(`/api/v1/cluster/${cluster}/keyspace/${keyspace}/table/${table}/row`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pk, updates })
            });

            if (response.ok) {
                currentData[rowIndex][col] = newValue;
                cell.innerHTML = formatCell(newValue);
                cell.classList.add('updated-flash');
                setTimeout(() => cell.classList.remove('updated-flash'), 1000);
            } else {
                const errorDetail = (await response.json()).detail || 'Failed to update row';
                Toast.error(errorDetail);
                cell.innerHTML = formatCell(rowData[col]);
            }
        } catch (error) {
            console.error('Update error:', error);
            Toast.error('Error updating row: ' + error.message);
            cell.innerHTML = formatCell(rowData[col]);
        } finally {
            cell.style.opacity = '1';
        }
    }

    function cancelEdit(cell, originalValue) {
        const input = cell.querySelector('.cell-editor');
        if (input) {
            cell.removeChild(input);
        }
    }

    // Initial load
    fetchData();

    // Event listeners
    document.getElementById('refresh-data').addEventListener('click', () => {
        pagingStack = [null];
        nextPagingState = null;
        fetchData();
    });

    nextPageBtn.addEventListener('click', () => fetchData('next'));
    prevPageBtn.addEventListener('click', () => fetchData('prev'));

    // Modal Helpers
    function closeModal(modal) {
        modal.classList.add('hidden');
    }

    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', () => {
            closeModal(insertRowModal);
            closeModal(deleteConfirmModal);
        });
    });

    // Row Deletion
    document.getElementById('menu-delete-row').addEventListener('click', () => {
        if (!activeCell) return;
        const rowIndex = activeCell.parentElement.dataset.index;
        confirmDeletion(rowIndex);
        contextMenu.classList.add('hidden');
    });

    function confirmDeletion(rowIndex) {
        const rowData = currentData[rowIndex];
        deletingRowIndex = rowIndex;

        let detailsHtml = '<ul>';
        pkCols.forEach(col => {
            detailsHtml += `<li><strong>${col}:</strong> ${rowData[col]}</li>`;
        });
        detailsHtml += '</ul>';

        deleteRowDetails.innerHTML = detailsHtml;
        deleteConfirmModal.classList.remove('hidden');
    }

    confirmDeleteBtn.addEventListener('click', async () => {
        if (deletingRowIndex === -1) return;

        const rowData = currentData[deletingRowIndex];
        const pk = {};
        pkCols.forEach(p => pk[p] = rowData[p]);

        try {
            confirmDeleteBtn.disabled = true;
            confirmDeleteBtn.textContent = 'Deleting...';

            const response = await fetch(`/api/v1/cluster/${cluster}/keyspace/${keyspace}/table/${table}/row`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(pk)
            });

            if (response.ok) {
                Toast.success('Row deleted successfully');
                closeModal(deleteConfirmModal);
                refreshAndFetch();
            } else {
                const error = await response.json();
                Toast.error(`Delete failed: ${error.detail}`);
            }
        } catch (err) {
            Toast.error(`Error: ${err.message}`);
        } finally {
            confirmDeleteBtn.disabled = false;
            confirmDeleteBtn.textContent = 'Delete Row';
            deletingRowIndex = -1;
        }
    });

    // Row Insertion
    insertRowBtn.addEventListener('click', async () => {
        if (!tableSchema) {
            try {
                const response = await fetch(`/api/v1/cluster/${cluster}/keyspace/${keyspace}/table/${table}`);
                tableSchema = await response.json();
            } catch (err) {
                Toast.error('Failed to fetch table schema');
                return;
            }
        }
        openInsertModal();
    });

    function openInsertModal() {
        const cols = tableSchema.columns;
        insertFormFields.innerHTML = Object.entries(cols).map(([name, type]) => {
            const isPK = pkCols.includes(name);
            const typeName = type.name || type;
            // Only show type if it's different from the column name
            const displayType = typeName.toLowerCase() === name.toLowerCase() ? '' : typeName;

            return `
                <div class="form-group">
                    <label>
                        ${name}
                        ${isPK ? '<span class="pk-badge" title="Primary Key">PK</span>' : ''}
                        ${displayType ? `<span class="type-hint">${displayType}</span>` : ''}
                    </label>
                    <input type="text" name="${name}" placeholder="Enter ${typeName}..." ${isPK ? 'required' : ''}>
                </div>
            `;
        }).join('');

        insertRowModal.classList.remove('hidden');
    }

    submitInsertBtn.addEventListener('click', async () => {
        const formData = new FormData(insertForm);
        const rowData = {};

        // Basic type conversion and filtering empty non-pk values
        for (let [name, val] of formData.entries()) {
            if (val === '' && !pkCols.includes(name)) continue;

            // Basic inference: if schema says it's a number, try to parse it
            const type = tableSchema.columns[name];
            const typeName = (type.name || type).toLowerCase();

            if (['int', 'bigint', 'float', 'double', 'decimal', 'varint'].includes(typeName)) {
                if (val !== '') rowData[name] = Number(val);
            } else if (['boolean'].includes(typeName)) {
                rowData[name] = val.toLowerCase() === 'true';
            } else {
                rowData[name] = val;
            }
        }

        try {
            submitInsertBtn.disabled = true;
            submitInsertBtn.textContent = 'Inserting...';

            const response = await fetch(`/api/v1/cluster/${cluster}/keyspace/${keyspace}/table/${table}/row`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(rowData)
            });

            if (response.ok) {
                Toast.success('Row inserted successfully');
                closeModal(insertRowModal);
                insertForm.reset();
                refreshAndFetch();
            } else {
                const error = await response.json();
                Toast.error(`Insert failed: ${error.detail}`);
            }
        } catch (err) {
            Toast.error(`Error: ${err.message}`);
        } finally {
            submitInsertBtn.disabled = false;
            submitInsertBtn.textContent = 'Insert Row';
        }
    });

});
