document.addEventListener('DOMContentLoaded', () => {
    const builder = document.querySelector('.builder-page');
    const cluster = builder.dataset.cluster;
    const keyspace = builder.dataset.keyspace;
    const mode = builder.dataset.mode || 'create';
    const existingSchema = builder.dataset.existingSchema
        ? JSON.parse(builder.dataset.existingSchema)
        : null;

    const tableNameInput = document.getElementById('table-name');
    const columnsList = document.getElementById('columns-list');
    const addColumnBtn = document.getElementById('add-column-btn');
    const cqlPreview = document.getElementById('cql-preview');
    const safetyReport = document.getElementById('safety-report');
    const actionBtn = document.getElementById('create-table-btn');

    const compactionSelect = document.getElementById('compaction-strategy');
    const ttlInput = document.getElementById('default-ttl');

    const compressionSelect = document.getElementById('compression');
    const gcGraceInput = document.getElementById('gc-grace-seconds');
    const bloomFilterInput = document.getElementById('bloom-filter-fp');
    const cachingSelect = document.getElementById('caching');
    const commentInput = document.getElementById('table-comment');
    const speculativeRetryInput = document.getElementById('speculative-retry');
    const cdcToggle = document.getElementById('cdc-toggle');
    const ifNotExistsToggle = document.getElementById('if-not-exists-toggle');
    const advancedToggleBtn = document.getElementById('advanced-options-toggle');
    const advancedBody = document.getElementById('advanced-options-body');

    const executeModal = document.getElementById('execute-modal');
    const confirmExecuteBtn = document.getElementById('confirm-execute-btn');
    const finalCqlConfirm = document.getElementById('final-cql-confirm');

    const primitiveTypes = [
        'ascii', 'bigint', 'blob', 'boolean', 'counter', 'date',
        'decimal', 'double', 'duration', 'float', 'inet', 'int',
        'smallint', 'text', 'time', 'timestamp', 'timeuuid',
        'tinyint', 'uuid', 'varchar', 'varint'
    ];

    const collectionTypes = [
        'list<>', 'set<>', 'map<,>', 'frozen<>', 'tuple<>', 'vector<float,>'
    ];

    const cassandraTypes = [...primitiveTypes, ...collectionTypes];

    const collectionSubtypes = [...primitiveTypes, 'list<>', 'set<>', 'map<,>'];

    let columns = [];
    let removedColumns = [];

    function createDefaultColumns() {
        return [
            createColumn('id', 'uuid', true, false),
            createColumn('created_at', 'timestamp', false, true),
            createColumn('data', 'text', false, false)
        ];
    }

    function createColumn(name, type, isPK, isCK, extra) {
        return {
            name: name,
            type: type,
            isPK: isPK,
            isCK: isCK,
            ckOrder: 'ASC',
            isStatic: false,
            hasSaiIndex: false,
            subType1: 'text',
            subType2: 'int',
            tupleTypes: '',
            vectorDimensions: 128,
            frozenInner: 'list<>',
            frozenInnerSub1: 'text',
            frozenInnerSub2: 'int',
            isExisting: false,
            isLocked: false,
            ...extra
        };
    }

    function isCollectionType(type) {
        return collectionTypes.includes(type);
    }

    function resolveFullType(col) {
        switch (col.type) {
            case 'list<>':
                return `list<${col.subType1}>`;
            case 'set<>':
                return `set<${col.subType1}>`;
            case 'map<,>':
                return `map<${col.subType1}, ${col.subType2}>`;
            case 'frozen<>':
                return `frozen<${resolveFrozenInner(col)}>`;
            case 'tuple<>':
                return `tuple<${col.tupleTypes || 'text'}>`;
            case 'vector<float,>':
                return `vector<float, ${col.vectorDimensions || 128}>`;
            default:
                return col.type;
        }
    }

    function resolveFrozenInner(col) {
        const inner = col.frozenInner || 'list<>';
        switch (inner) {
            case 'list<>':
                return `list<${col.frozenInnerSub1 || 'text'}>`;
            case 'set<>':
                return `set<${col.frozenInnerSub1 || 'text'}>`;
            case 'map<,>':
                return `map<${col.frozenInnerSub1 || 'text'}, ${col.frozenInnerSub2 || 'int'}>`;
            default:
                return inner;
        }
    }

    function buildTypeOptions(selectedType) {
        return cassandraTypes.map(t => {
            const label = t;
            const selected = selectedType === t ? 'selected' : '';
            return `<option value="${escapeHtml(t)}" ${selected}>${escapeHtml(label)}</option>`;
        }).join('');
    }

    function buildPrimitiveOptions(selectedType) {
        return primitiveTypes.map(t => {
            const selected = selectedType === t ? 'selected' : '';
            return `<option value="${escapeHtml(t)}" ${selected}>${escapeHtml(t)}</option>`;
        }).join('');
    }

    function buildCollectionSubtypeOptions(selectedType) {
        return collectionSubtypes.map(t => {
            const selected = selectedType === t ? 'selected' : '';
            return `<option value="${escapeHtml(t)}" ${selected}>${escapeHtml(t)}</option>`;
        }).join('');
    }

    function buildFrozenInnerOptions(selectedType) {
        const options = ['list<>', 'set<>', 'map<,>', ...primitiveTypes];
        return options.map(t => {
            const selected = selectedType === t ? 'selected' : '';
            return `<option value="${escapeHtml(t)}" ${selected}>${escapeHtml(t)}</option>`;
        }).join('');
    }

    function buildSubTypePicker(col, idx) {
        switch (col.type) {
            case 'list<>':
            case 'set<>':
                return `
                    <div class="sub-type-row">
                        <label class="sub-type-label">Inner type:</label>
                        <select class="sub-type-select col-sub1-select">${buildPrimitiveOptions(col.subType1)}</select>
                    </div>`;
            case 'map<,>':
                return `
                    <div class="sub-type-row">
                        <label class="sub-type-label">Key type:</label>
                        <select class="sub-type-select col-sub1-select">${buildPrimitiveOptions(col.subType1)}</select>
                        <label class="sub-type-label">Value type:</label>
                        <select class="sub-type-select col-sub2-select">${buildPrimitiveOptions(col.subType2)}</select>
                    </div>`;
            case 'frozen<>':
                return `
                    <div class="sub-type-row">
                        <label class="sub-type-label">Frozen inner:</label>
                        <select class="sub-type-select col-frozen-inner-select">${buildFrozenInnerOptions(col.frozenInner)}</select>
                        ${buildFrozenSubPickers(col)}
                    </div>`;
            case 'tuple<>':
                return `
                    <div class="sub-type-row">
                        <label class="sub-type-label">Types (comma-separated):</label>
                        <input type="text" class="col-tuple-input sub-type-input" value="${escapeHtml(col.tupleTypes)}" placeholder="text, int, timestamp">
                    </div>`;
            case 'vector<float,>':
                return `
                    <div class="sub-type-row">
                        <label class="sub-type-label">Dimensions:</label>
                        <input type="number" class="col-vector-dim-input sub-type-input" value="${col.vectorDimensions}" min="1" placeholder="128">
                    </div>`;
            default:
                return '';
        }
    }

    function buildFrozenSubPickers(col) {
        const inner = col.frozenInner || 'list<>';
        if (inner === 'list<>' || inner === 'set<>') {
            return `
                <label class="sub-type-label">Inner type:</label>
                <select class="sub-type-select col-frozen-sub1-select">${buildPrimitiveOptions(col.frozenInnerSub1)}</select>`;
        }
        if (inner === 'map<,>') {
            return `
                <label class="sub-type-label">Key:</label>
                <select class="sub-type-select col-frozen-sub1-select">${buildPrimitiveOptions(col.frozenInnerSub1)}</select>
                <label class="sub-type-label">Value:</label>
                <select class="sub-type-select col-frozen-sub2-select">${buildPrimitiveOptions(col.frozenInnerSub2)}</select>`;
        }
        return '';
    }

    function renderColumns() {
        columnsList.innerHTML = columns.map((col, idx) => {
            const isKey = col.isPK || col.isCK;
            const locked = col.isLocked;
            const showStatic = !isKey;
            const showSai = !col.isPK;
            const hasSubType = isCollectionType(col.type);
            const showCkOrder = col.isCK;

            return `
            <div class="column-row-wrapper" data-index="${idx}">
                <div class="column-row ${locked ? 'locked-row' : ''}">
                    <input type="text" value="${escapeHtml(col.name)}" placeholder="Column Name"
                        class="col-name-input" autocomplete="off" ${locked ? 'readonly' : ''}>
                    <select class="col-type-select" ${locked ? 'disabled' : ''}>
                        ${buildTypeOptions(col.type)}
                    </select>
                    <label class="pill-checkbox ${col.isPK ? 'active' : ''} ${locked ? 'pill-locked' : ''}">
                        <input type="checkbox" class="col-pk-check" ${col.isPK ? 'checked' : ''} ${locked ? 'disabled' : ''}>
                        <span>PK</span>
                    </label>
                    <label class="pill-checkbox ${col.isCK ? 'active' : ''} ${locked ? 'pill-locked' : ''}">
                        <input type="checkbox" class="col-ck-check" ${col.isCK ? 'checked' : ''} ${locked ? 'disabled' : ''}>
                        <span>CK</span>
                    </label>
                    ${showCkOrder ? `
                        <button class="ck-order-btn ${col.ckOrder === 'DESC' ? 'desc' : ''}" title="Clustering Order: ${col.ckOrder}">
                            ${col.ckOrder}
                        </button>
                    ` : '<span class="ck-order-placeholder"></span>'}
                    ${showStatic ? `
                        <label class="pill-checkbox pill-sm ${col.isStatic ? 'active' : ''}">
                            <input type="checkbox" class="col-static-check" ${col.isStatic ? 'checked' : ''}>
                            <span>Static</span>
                        </label>
                    ` : '<span class="static-placeholder"></span>'}
                    ${showSai ? `
                        <label class="pill-checkbox pill-sm ${col.hasSaiIndex ? 'active' : ''}">
                            <input type="checkbox" class="col-sai-check" ${col.hasSaiIndex ? 'checked' : ''}>
                            <span>SAI</span>
                        </label>
                    ` : '<span class="sai-placeholder"></span>'}
                    <button class="btn-icon-danger remove-col-btn" title="Remove Column"
                        ${(columns.length <= 1 || locked) ? 'disabled' : ''}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"></path>
                        </svg>
                    </button>
                </div>
                ${hasSubType ? buildSubTypePicker(col, idx) : ''}
            </div>`;
        }).join('');

        attachColumnEvents();
        updatePreview();
    }

    function attachColumnEvents() {
        const wrappers = columnsList.querySelectorAll('.column-row-wrapper');
        wrappers.forEach(wrapper => {
            const idx = parseInt(wrapper.dataset.index);
            const col = columns[idx];

            wrapper.querySelector('.col-name-input').addEventListener('input', (e) => {
                columns[idx].name = e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '');
                e.target.value = columns[idx].name;
                updatePreview();
            });

            wrapper.querySelector('.col-type-select').addEventListener('change', (e) => {
                columns[idx].type = e.target.value;
                renderColumns();
            });

            const pkCheck = wrapper.querySelector('.col-pk-check');
            if (pkCheck && !pkCheck.disabled) {
                pkCheck.addEventListener('change', (e) => {
                    columns[idx].isPK = e.target.checked;
                    if (e.target.checked) {
                        columns[idx].isCK = false;
                        columns[idx].isStatic = false;
                    }
                    renderColumns();
                });
            }

            const ckCheck = wrapper.querySelector('.col-ck-check');
            if (ckCheck && !ckCheck.disabled) {
                ckCheck.addEventListener('change', (e) => {
                    columns[idx].isCK = e.target.checked;
                    if (e.target.checked) {
                        columns[idx].isPK = false;
                        columns[idx].isStatic = false;
                    }
                    renderColumns();
                });
            }

            const ckOrderBtn = wrapper.querySelector('.ck-order-btn');
            if (ckOrderBtn) {
                ckOrderBtn.addEventListener('click', () => {
                    columns[idx].ckOrder = columns[idx].ckOrder === 'ASC' ? 'DESC' : 'ASC';
                    renderColumns();
                });
            }

            const staticCheck = wrapper.querySelector('.col-static-check');
            if (staticCheck) {
                staticCheck.addEventListener('change', (e) => {
                    columns[idx].isStatic = e.target.checked;
                    updatePreview();
                });
            }

            const saiCheck = wrapper.querySelector('.col-sai-check');
            if (saiCheck) {
                saiCheck.addEventListener('change', (e) => {
                    columns[idx].hasSaiIndex = e.target.checked;
                    updatePreview();
                });
            }

            wrapper.querySelector('.remove-col-btn')?.addEventListener('click', () => {
                const removed = columns.splice(idx, 1)[0];
                if (mode === 'alter' && removed.isExisting) {
                    removedColumns.push(removed);
                }
                renderColumns();
            });

            attachSubTypeEvents(wrapper, idx);
        });
    }

    function attachSubTypeEvents(wrapper, idx) {
        const col = columns[idx];

        const sub1 = wrapper.querySelector('.col-sub1-select');
        if (sub1) {
            sub1.addEventListener('change', (e) => {
                columns[idx].subType1 = e.target.value;
                updatePreview();
            });
        }

        const sub2 = wrapper.querySelector('.col-sub2-select');
        if (sub2) {
            sub2.addEventListener('change', (e) => {
                columns[idx].subType2 = e.target.value;
                updatePreview();
            });
        }

        const frozenInner = wrapper.querySelector('.col-frozen-inner-select');
        if (frozenInner) {
            frozenInner.addEventListener('change', (e) => {
                columns[idx].frozenInner = e.target.value;
                renderColumns();
            });
        }

        const frozenSub1 = wrapper.querySelector('.col-frozen-sub1-select');
        if (frozenSub1) {
            frozenSub1.addEventListener('change', (e) => {
                columns[idx].frozenInnerSub1 = e.target.value;
                updatePreview();
            });
        }

        const frozenSub2 = wrapper.querySelector('.col-frozen-sub2-select');
        if (frozenSub2) {
            frozenSub2.addEventListener('change', (e) => {
                columns[idx].frozenInnerSub2 = e.target.value;
                updatePreview();
            });
        }

        const tupleInput = wrapper.querySelector('.col-tuple-input');
        if (tupleInput) {
            tupleInput.addEventListener('input', (e) => {
                columns[idx].tupleTypes = e.target.value;
                updatePreview();
            });
        }

        const vectorInput = wrapper.querySelector('.col-vector-dim-input');
        if (vectorInput) {
            vectorInput.addEventListener('input', (e) => {
                columns[idx].vectorDimensions = parseInt(e.target.value) || 128;
                updatePreview();
            });
        }
    }

    function generateCQL() {
        if (mode === 'alter') {
            return generateAlterCQL();
        }
        return generateCreateCQL();
    }

    function generateCreateCQL() {
        const tableName = tableNameInput.value.trim() || 'unset_table_name';
        const pkCols = columns.filter(c => c.isPK);
        const ckCols = columns.filter(c => c.isCK);

        if (pkCols.length === 0) return '-- Error: Missing Partition Key (PK)';

        const ifne = ifNotExistsToggle.checked ? ' IF NOT EXISTS' : '';
        let cql = `CREATE TABLE${ifne} "${keyspace}"."${tableName}" (\n`;

        columns.forEach(col => {
            const fullType = resolveFullType(col);
            const staticMod = col.isStatic ? ' STATIC' : '';
            cql += `  ${col.name} ${fullType}${staticMod},\n`;
        });

        const pkNames = pkCols.map(c => c.name);
        const ckNames = ckCols.map(c => c.name);
        const pkString = pkNames.length > 1 ? `(${pkNames.join(', ')})` : pkNames[0];
        const fullPK = ckNames.length > 0 ? `(${pkString}, ${ckNames.join(', ')})` : `(${pkString})`;
        cql += `  PRIMARY KEY ${fullPK}\n)`;

        const options = buildTableOptions();
        const hasDescCK = ckCols.some(c => c.ckOrder === 'DESC');
        if (hasDescCK) {
            const orderParts = ckCols.map(c => `${c.name} ${c.ckOrder}`);
            options.unshift(`CLUSTERING ORDER BY (${orderParts.join(', ')})`);
        }

        if (options.length > 0) {
            cql += `\nWITH ${options.join('\n  AND ')}`;
        }
        cql += ';';

        const saiStatements = buildSaiStatements(tableName);
        if (saiStatements.length > 0) {
            cql += '\n\n' + saiStatements.join('\n');
        }

        return cql;
    }

    function generateAlterCQL() {
        const tableName = tableNameInput.value.trim() || 'unset_table_name';
        const fqTable = `"${keyspace}"."${tableName}"`;
        const statements = [];

        const newCols = columns.filter(c => !c.isExisting);
        newCols.forEach(col => {
            const fullType = resolveFullType(col);
            const staticMod = col.isStatic ? ' STATIC' : '';
            statements.push(`ALTER TABLE ${fqTable} ADD ${col.name} ${fullType}${staticMod};`);
        });

        removedColumns.forEach(col => {
            statements.push(`ALTER TABLE ${fqTable} DROP ${col.name};`);
        });

        const options = buildTableOptions();
        if (options.length > 0) {
            statements.push(`ALTER TABLE ${fqTable}\n  WITH ${options.join('\n  AND ')};`);
        }

        const saiStatements = buildSaiStatements(tableName);
        if (saiStatements.length > 0) {
            statements.push(...saiStatements);
        }

        if (statements.length === 0) {
            return '-- No changes detected';
        }

        return statements.join('\n\n');
    }

    function buildTableOptions() {
        const options = [];

        if (compactionSelect.value) {
            options.push(`compaction = {'class': '${compactionSelect.value}'}`);
        }
        if (ttlInput.value && parseInt(ttlInput.value) > 0) {
            options.push(`default_time_to_live = ${ttlInput.value}`);
        }

        const compression = compressionSelect.value;
        if (compression === 'none') {
            options.push(`compression = {'enabled': 'false'}`);
        } else if (compression) {
            options.push(`compression = {'class': 'org.apache.cassandra.io.compress.${compression}'}`);
        }

        if (gcGraceInput.value && gcGraceInput.value.trim() !== '') {
            options.push(`gc_grace_seconds = ${gcGraceInput.value}`);
        }
        if (bloomFilterInput.value && bloomFilterInput.value.trim() !== '') {
            options.push(`bloom_filter_fp_chance = ${bloomFilterInput.value}`);
        }

        const caching = cachingSelect.value;
        if (caching) {
            const cachingMap = {
                'ALL': `{'keys': 'ALL', 'rows_per_partition': 'ALL'}`,
                'KEYS_ONLY': `{'keys': 'ALL', 'rows_per_partition': 'NONE'}`,
                'ROWS_ONLY': `{'keys': 'NONE', 'rows_per_partition': 'ALL'}`,
                'NONE': `{'keys': 'NONE', 'rows_per_partition': 'NONE'}`
            };
            if (caching !== 'ALL') {
                options.push(`caching = ${cachingMap[caching]}`);
            }
        }

        if (commentInput.value && commentInput.value.trim() !== '') {
            const escaped = commentInput.value.replace(/'/g, "''");
            options.push(`comment = '${escaped}'`);
        }
        if (speculativeRetryInput.value && speculativeRetryInput.value.trim() !== '') {
            const escaped = speculativeRetryInput.value.replace(/'/g, "''");
            options.push(`speculative_retry = '${escaped}'`);
        }
        if (cdcToggle.checked) {
            options.push(`cdc = true`);
        }

        return options;
    }

    function buildSaiStatements(tableName) {
        const saiCols = columns.filter(c => c.hasSaiIndex && !c.isPK);
        return saiCols.map(col =>
            `CREATE INDEX IF NOT EXISTS ON "${keyspace}"."${tableName}" ("${col.name}") USING 'sai';`
        );
    }

    function updatePreview() {
        const cql = generateCQL();
        cqlPreview.textContent = cql;

        const isValid = tableNameInput.value.trim().length > 0 &&
            columns.some(c => c.isPK) &&
            columns.every(c => c.name.length > 0);

        actionBtn.disabled = !isValid;
        analyzeSafety();
    }

    function analyzeSafety() {
        const pk = columns.filter(c => c.isPK);
        const ck = columns.filter(c => c.isCK);

        if (tableNameInput.value.trim().length === 0) {
            safetyReport.innerHTML = 'Specify a table name.';
            safetyReport.className = 'safety-message';
            return;
        }

        if (pk.length === 0) {
            safetyReport.innerHTML = '<strong>Table must have at least one Partition Key (PK).</strong>';
            safetyReport.className = 'safety-message warning';
            return;
        }

        const findings = [];

        if (pk.length === 1 && (pk[0].type === 'text' || pk[0].type === 'uuid')) {
            findings.push('Standard distribution detected for ' + escapeHtml(pk[0].name) + ' partition.');
        }

        if (pk.some(p => p.type === 'boolean')) {
            findings.push('<strong>High risk detected:</strong> Partitioning on a boolean field will create a massive hot-spot (only 2 partitions total).');
        }

        const nonKeyCols = columns.filter(c => !c.isPK && !c.isCK);
        const hasCounter = nonKeyCols.some(c => c.type === 'counter');
        const allCounter = nonKeyCols.length > 0 && nonKeyCols.every(c => c.type === 'counter');
        if (hasCounter && !allCounter) {
            findings.push('<strong>Counter table violation:</strong> Counter tables require all non-key columns to be counter type.');
        }

        if (findings.length === 0) {
            safetyReport.innerHTML = 'Schema looks healthy. Ready to deploy.';
            safetyReport.className = 'safety-message';
        } else {
            const hasRisk = findings.some(f => f.includes('risk') || f.includes('violation'));
            safetyReport.innerHTML = findings.join('<br>');
            safetyReport.className = 'safety-message ' + (hasRisk ? 'warning' : '');
        }
    }

    function initAlterMode() {
        if (!existingSchema) return;

        const heading = builder.querySelector('.builder-header h1');
        heading.textContent = 'Edit Table: ' + tableNameInput.value;
        tableNameInput.readOnly = true;

        actionBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 12h14M12 5l7 7-7 7"></path>
            </svg>
            Apply Changes`;

        confirmExecuteBtn.textContent = 'Confirm & Apply';

        const pkSet = new Set(existingSchema.partition_key || []);
        const ckSet = new Set(existingSchema.clustering_key || []);
        const ckOrder = existingSchema.clustering_order || {};

        columns = [];
        for (const [colName, colType] of Object.entries(existingSchema.columns)) {
            const isPK = pkSet.has(colName);
            const isCK = ckSet.has(colName);
            const parsed = parseExistingType(colType);
            columns.push(createColumn(colName, parsed.type, isPK, isCK, {
                ckOrder: ckOrder[colName] || 'ASC',
                isExisting: true,
                isLocked: isPK || isCK,
                ...parsed.extra
            }));
        }

        if (existingSchema.options) {
            const opts = existingSchema.options;
            if (opts.compaction) compactionSelect.value = opts.compaction;
            if (opts.default_ttl) ttlInput.value = opts.default_ttl;
            if (opts.compression) compressionSelect.value = opts.compression;
            if (opts.gc_grace_seconds) gcGraceInput.value = opts.gc_grace_seconds;
            if (opts.comment) commentInput.value = opts.comment;
        }
    }

    function parseExistingType(typeStr) {
        const lower = typeStr.toLowerCase().trim();

        const listMatch = lower.match(/^list<(\w+)>$/);
        if (listMatch) return { type: 'list<>', extra: { subType1: listMatch[1] } };

        const setMatch = lower.match(/^set<(\w+)>$/);
        if (setMatch) return { type: 'set<>', extra: { subType1: setMatch[1] } };

        const mapMatch = lower.match(/^map<(\w+),\s*(\w+)>$/);
        if (mapMatch) return { type: 'map<,>', extra: { subType1: mapMatch[1], subType2: mapMatch[2] } };

        const tupleMatch = lower.match(/^tuple<(.+)>$/);
        if (tupleMatch) return { type: 'tuple<>', extra: { tupleTypes: tupleMatch[1] } };

        const vectorMatch = lower.match(/^vector<float,\s*(\d+)>$/);
        if (vectorMatch) return { type: 'vector<float,>', extra: { vectorDimensions: parseInt(vectorMatch[1]) } };

        const frozenMatch = lower.match(/^frozen<(.+)>$/);
        if (frozenMatch) {
            const inner = frozenMatch[1];
            const innerList = inner.match(/^list<(\w+)>$/);
            if (innerList) return { type: 'frozen<>', extra: { frozenInner: 'list<>', frozenInnerSub1: innerList[1] } };
            const innerSet = inner.match(/^set<(\w+)>$/);
            if (innerSet) return { type: 'frozen<>', extra: { frozenInner: 'set<>', frozenInnerSub1: innerSet[1] } };
            const innerMap = inner.match(/^map<(\w+),\s*(\w+)>$/);
            if (innerMap) return { type: 'frozen<>', extra: { frozenInner: 'map<,>', frozenInnerSub1: innerMap[1], frozenInnerSub2: innerMap[2] } };
            return { type: 'frozen<>', extra: { frozenInner: inner } };
        }

        return { type: typeStr, extra: {} };
    }

    // --- Event listeners ---

    addColumnBtn.addEventListener('click', () => {
        columns.push(createColumn('new_col_' + columns.length, 'text', false, false));
        renderColumns();
    });

    tableNameInput.addEventListener('input', updatePreview);
    compactionSelect.addEventListener('change', updatePreview);
    ttlInput.addEventListener('input', updatePreview);
    compressionSelect.addEventListener('change', updatePreview);
    gcGraceInput.addEventListener('input', updatePreview);
    bloomFilterInput.addEventListener('input', updatePreview);
    cachingSelect.addEventListener('change', updatePreview);
    commentInput.addEventListener('input', updatePreview);
    speculativeRetryInput.addEventListener('input', updatePreview);
    cdcToggle.addEventListener('change', updatePreview);
    ifNotExistsToggle.addEventListener('change', updatePreview);

    advancedToggleBtn.addEventListener('click', () => {
        const isHidden = advancedBody.classList.toggle('hidden');
        advancedToggleBtn.classList.toggle('expanded', !isHidden);
    });

    actionBtn.addEventListener('click', () => {
        finalCqlConfirm.textContent = generateCQL();
        executeModal.classList.remove('hidden');
    });

    confirmExecuteBtn.addEventListener('click', async () => {
        const cql = generateCQL();
        try {
            confirmExecuteBtn.disabled = true;
            confirmExecuteBtn.textContent = 'Executing...';

            if (mode === 'alter') {
                const statements = cql.split(/;\s*\n/).map(s => s.trim()).filter(s => s && !s.startsWith('--'));
                for (const stmt of statements) {
                    const cleanStmt = stmt.endsWith(';') ? stmt : stmt + ';';
                    const response = await fetch(`/api/v1/cluster/${cluster}/operations/cqlsh`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ cql: cleanStmt })
                    });
                    if (!response.ok) {
                        const err = await response.json();
                        throw new Error(err.detail || 'Failed to execute: ' + cleanStmt);
                    }
                }
                Toast.success('Table altered successfully!');
            } else {
                const statements = cql.split(/;\s*\n/).map(s => s.trim()).filter(s => s && !s.startsWith('--'));
                for (const stmt of statements) {
                    const cleanStmt = stmt.endsWith(';') ? stmt : stmt + ';';
                    const response = await fetch(`/api/v1/cluster/${cluster}/operations/cqlsh`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ cql: cleanStmt })
                    });
                    if (!response.ok) {
                        const err = await response.json();
                        throw new Error(err.detail || 'Failed to execute: ' + cleanStmt);
                    }
                }
                Toast.success('Table created successfully!');
            }

            setTimeout(() => {
                window.location.href = `/cluster/${cluster}/keyspace/${keyspace}`;
            }, 1500);
        } catch (e) {
            Toast.error('Execution failed: ' + e.message);
        } finally {
            confirmExecuteBtn.disabled = false;
            confirmExecuteBtn.textContent = mode === 'alter' ? 'Confirm & Apply' : 'Confirm & Create';
        }
    });

    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            if (modal) modal.classList.add('hidden');
        });
    });

    // --- Initialization ---

    if (mode === 'alter') {
        initAlterMode();
    } else {
        columns = createDefaultColumns();
    }

    renderColumns();
});
