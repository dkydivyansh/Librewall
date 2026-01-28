const WidgetLoader = {
    registry: [],
    loadedWidgets: {},
    visibility: {},
    wsPort: null,
    networkEnabled: false,

    async loadRegistry() {
        try {
            const response = await fetch('/widgets/index.json');
            if (!response.ok) throw new Error('Registry not found');
            const data = await response.json();
            this.registry = data.widgets || [];
            console.log(`Widget registry loaded: ${this.registry.length} widgets`);
            return this.registry;
        } catch (e) {
            console.error('Failed to load widget registry:', e);
            return [];
        }
    },

    async loadWidget(widgetInfo) {
        const { id, folder } = widgetInfo;
        if (this.loadedWidgets[id]) return this.loadedWidgets[id];

        try {

            const cssPath = `/widgets/${folder}/style.css`;
            if (!document.querySelector(`link[href="${cssPath}"]`)) {
                const link = document.createElement('link');
                link.rel = 'stylesheet';
                link.href = cssPath;
                link.id = `widget-css-${id}`;
                document.head.appendChild(link);
            }

            const jsPath = `/widgets/${folder}/main.js`;
            await new Promise((resolve, reject) => {
                if (document.querySelector(`script[src="${jsPath}"]`)) {
                    resolve();
                    return;
                }
                const script = document.createElement('script');
                script.src = jsPath;
                script.id = `widget-js-${id}`;
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            });

            const camelId = this.camelCase(id);
            const funcNames = [
                `getWidgetContent_${camelId}`,
                `getWidgetContent_${id}`,
                `getWidgetContent_${id.replace(/-/g, '')}`
            ];

            let getContent = null;
            for (const funcName of funcNames) {
                if (typeof window[funcName] === 'function') {
                    getContent = window[funcName];
                    break;
                }
            }

            if (getContent) {
                this.loadedWidgets[id] = getContent();
                console.log(`Widget loaded: ${id}`);
                widgetInfo.status = 'loaded';
                return this.loadedWidgets[id];
            } else {
                console.warn(`Widget ${id} missing getWidgetContent function. Tried: ${funcNames.join(', ')}`);
                widgetInfo.status = 'error';
                widgetInfo.errorMsg = 'Corrupted: Missing function';
                return null;
            }
        } catch (e) {
            console.error(`Failed to load widget ${id}:`, e);
            widgetInfo.status = 'missing';
            return null;
        }
    },

    camelCase(str) {
        return str.replace(/-([a-z])/g, (g) => g[1].toUpperCase());
    },

    renderWidget(id, content, wrapper) {

        const containerId = id === 'clock' ? 'live-clock' : id;

        let container = document.getElementById(containerId);
        if (!container) {
            container = document.createElement('div');
            container.id = containerId;
            container.className = 'widget-container';
            wrapper.appendChild(container);
        }

        if (content.settings) {
            if (content.settings.minWidth) {
                container.style.minWidth = content.settings.minWidth;
            }
            if (content.settings.minHeight) {
                container.style.minHeight = content.settings.minHeight;
            }
        }

        container.innerHTML = content.html + '<div class="resize-handle"></div>';

        if (typeof content.init === 'function') {
            content.init();
        }

        return container;
    },

    unloadWidget(id) {
        const widget = this.loadedWidgets[id];
        if (widget && typeof widget.destroy === 'function') {
            widget.destroy();
        }

        const containerId = id === 'clock' ? 'live-clock' : id;
        const container = document.getElementById(containerId);
        if (container) {
            container.style.display = 'none';
        }
    },

    async savePositions() {
        const positions = {};
        document.querySelectorAll('.widget-container').forEach(el => {
            positions[el.id] = {
                left: el.style.left,
                top: el.style.top
            };
        });

        try {
            const response = await fetch('/save_widget_positions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(positions)
            });
            if (response.ok) console.log('Positions saved');
        } catch (e) {
            console.error('Error saving positions:', e);
        }
    },

    async restorePositions() {
        try {
            const response = await fetch('/widget.json');
            let positions = {};

            if (response.ok) {
                positions = await response.json();
            }

            if (!positions || Object.keys(positions).length === 0) {
                console.log("No saved positions found. Adding default Clock widget.");
                const clockId = 'live-clock';
                const clockWidth = 300;

                const centerX = (window.innerWidth / 2) - (clockWidth / 2);

                positions = {
                    [clockId]: {
                        left: `${Math.max(0, centerX)}px`,
                        top: '40px'
                    }
                };

                this.visibility[clockId] = true;
                this.saveVisibility();
            }

            Object.entries(positions).forEach(([id, pos]) => {
                const el = document.getElementById(id);
                if (el) {
                    el.style.left = pos.left;
                    el.style.top = pos.top;
                    el.style.position = 'absolute';
                }
            });
        } catch (e) {
            console.error('Error restoring positions:', e);
        }
    },

    async saveVisibility() {
        try {
            const response = await fetch('/save_widget_visibility', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.visibility)
            });
            if (response.ok) console.log('Widget visibility saved');
        } catch (e) {
            console.error('Error saving visibility:', e);
        }
    },

    async restoreVisibility() {
        let hasVisibilityConfig = false;
        try {
            const response = await fetch('/widget_visibility.json');
            if (response.ok) {
                this.visibility = await response.json();
                hasVisibilityConfig = Object.keys(this.visibility).length > 0;
            }
        } catch (e) {

        }

        this.registry.forEach(w => {
            const containerId = w.id === 'clock' ? 'live-clock' : w.id;

            if (this.visibility[containerId] === undefined) {

                if (!hasVisibilityConfig && containerId === 'live-clock') {
                    this.visibility[containerId] = true;
                } else {
                    this.visibility[containerId] = false;

                }
            }

            const el = document.getElementById(containerId);
            if (el) {
                el.style.display = this.visibility[containerId] ? '' : 'none';
            }
        });

        if (!hasVisibilityConfig) {
            this.saveVisibility();
        }
    },

    toggleVisibility(widgetId, visible) {
        const el = document.getElementById(widgetId);
        if (el) {
            el.style.display = visible ? '' : 'none';
            this.visibility[widgetId] = visible;
        }
    },

    async init() {
        this.showLoading();
        await this.loadRegistry();
        await this.loadWidgetStyles();

        const wrapper = document.getElementById('widget-wrapper');
        if (!wrapper) {
            console.error('widget-wrapper not found');
            return;
        }

        try {
            const configResponse = await fetch('/config');
            const config = await configResponse.json();
            this.networkEnabled = config.Enable_Global_Widget === true || config.Enable_Network_Widget === true;
        } catch (e) {
            this.networkEnabled = true;
        }

        for (const widgetInfo of this.registry) {
            const content = await this.loadWidget(widgetInfo);
            if (content) {
                this.renderWidget(widgetInfo.id, content, wrapper);
            }
        }

        this.registry = this.registry.filter(w => w.status !== 'missing');

        if (this.networkEnabled) {
            await this.restorePositions();
            await this.restoreVisibility();
            await this.initNetworkConnection();
        } else {
            await this.restorePositions();
            await this.restoreVisibility();

            ['traffic-data', 'listening-ports', 'live-traffic-log', 'active-connections'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.style.display = 'none';
            });
        }

        this.initDraggableSystem();
        this.initEditMenu();
        this.initContextMenu();
        this.initSettingsEditor();
        this.populateEditMenu();
        this.initWidgetSearch();
        this.setupWidgetClickHandlers();

        setTimeout(() => this.hideLoading(), 500);
    },

    showLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.opacity = '1';
            overlay.style.pointerEvents = 'all';
        }
    },

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.opacity = '0';
            overlay.style.pointerEvents = 'none';

            setTimeout(() => {

            }, 500);
        }
    },

    setupWidgetClickHandlers() {
        document.querySelectorAll('.widget-container').forEach(container => {
            container.addEventListener('click', (e) => {

                if (this.isDraggable && e.button === 0) {

                    if (e.target.closest('button, input, a, canvas, .resize-handle')) return;

                    let widgetId = container.id;
                    if (widgetId === 'live-clock') widgetId = 'clock';

                    this.showContextMenu(widgetId, e.clientX, e.clientY);
                    e.stopPropagation();
                }
            });
        });
    },

    populateEditMenu() {
        const list = document.getElementById('widget-toggle-list');
        if (!list) return;

        list.innerHTML = '';
        this.registry.forEach(w => {
            const containerId = w.id === 'clock' ? 'live-clock' : w.id;
            const checked = this.visibility[containerId] !== false ? 'checked' : '';

            const widget = this.loadedWidgets[w.id];
            const hasEditableSettings = widget?.editableSettings && widget.editableSettings.length > 0;
            const isError = w.status === 'error';

            const label = document.createElement('label');
            label.className = 'widget-toggle';
            label.innerHTML = `
                <input type="checkbox" data-widget="${containerId}" ${checked} ${isError ? 'disabled' : ''}>
                <span>${w.name}</span>
                ${isError ? '<span class="widget-error-icon" title="Corrupted: Missing Data" style="color: #ff4444; margin-left: 8px;">⚠️</span>' : ''}
                ${hasEditableSettings && !isError ? `
                <button class="widget-edit-btn" data-widget-id="${w.id}" title="Edit Settings">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="3"/>
                        <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>
                    </svg>
                </button>
                ` : ''}
            `;
            list.appendChild(label);
        });

        list.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const widgetId = e.target.getAttribute('data-widget');
                if (widgetId) {
                    this.toggleVisibility(widgetId, e.target.checked);
                }
            });
        });

        list.querySelectorAll('.widget-edit-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const widgetId = btn.getAttribute('data-widget-id');
                this.openSettingsEditor(widgetId);
            });
        });
    },

    initWidgetSearch() {
        const searchInput = document.getElementById('widget-search');
        if (!searchInput) return;

        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            const toggles = document.querySelectorAll('.widget-toggle');

            toggles.forEach(toggle => {
                const name = toggle.querySelector('span')?.textContent.toLowerCase() || '';
                toggle.style.display = name.includes(query) ? 'flex' : 'none';
            });
        });
    },

    async initNetworkConnection() {
        try {
            const appConfigResponse = await fetch('/app_config.json');
            const appConfig = await appConfigResponse.json();
            this.wsPort = appConfig.ws_port;

            if (this.wsPort) {
                this.connectWebSocket(this.wsPort);
            }
        } catch (e) {
            console.error('Failed to init network connection:', e);
        }
    },

    connectWebSocket(port) {
        const wsStatus = document.getElementById('ws-status');
        if (wsStatus) {
            wsStatus.textContent = 'Connecting...';
            wsStatus.className = '';
        }

        const socket = new WebSocket(`ws://localhost:${port}`);

        socket.onopen = () => {
            console.log('WebSocket connected');
            if (wsStatus) {
                wsStatus.textContent = 'Connected';
                wsStatus.className = 'connected';
            }
        };

        socket.onmessage = (event) => {
            this.updateNetworkUI(JSON.parse(event.data));
        };

        socket.onclose = () => {
            if (wsStatus) {
                wsStatus.textContent = 'Disconnected';
                wsStatus.className = 'error';
            }
            setTimeout(() => this.connectWebSocket(port), 3000);
        };

        socket.onerror = () => {
            if (wsStatus) {
                wsStatus.textContent = 'Error';
                wsStatus.className = 'error';
            }
        };
    },

    formatBits(bits, perSecond = false) {
        if (!bits || bits === 0) return '0 ' + (perSecond ? 'bps' : 'b');
        const k = 1000;
        const sizes = perSecond ? ['bps', 'Kbps', 'Mbps', 'Gbps', 'Tbps'] : ['b', 'Kb', 'Mb', 'Gb', 'Tb'];
        const i = Math.floor(Math.log(bits) / Math.log(k));
        return `${parseFloat((bits / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
    },

    formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
    },

    updateNetworkUI(data) {
        try {
            const uploadEl = document.getElementById('upload-speed');
            const downloadEl = document.getElementById('download-speed');
            const totalSentEl = document.getElementById('total-sent');
            const totalRecvEl = document.getElementById('total-recv');

            if (uploadEl) uploadEl.textContent = this.formatBits(data.upload_bps, true);
            if (downloadEl) downloadEl.textContent = this.formatBits(data.download_bps, true);
            if (totalSentEl) totalSentEl.textContent = this.formatBytes(data.total_sent);
            if (totalRecvEl) totalRecvEl.textContent = this.formatBytes(data.total_recv);

            const listeningCount = document.getElementById('listening-count');
            const listeningList = document.getElementById('listening-list');
            if (listeningCount) listeningCount.textContent = `(${data.listening_count})`;
            if (listeningList) {
                let html = '';
                if (data.listening_ports.length === 0) {
                    html = 'No listening ports found.';
                } else {
                    html += 'Port/Protocol'.padEnd(15) + 'Type'.padEnd(15) + 'Process\n';
                    data.listening_ports.forEach(item => {
                        let port = (item.port + ' (' + item.protocol + ')').padEnd(15);
                        html += `${port}${item.type.padEnd(15)}${item.process}\n`;
                    });
                }
                listeningList.textContent = html;
            }

            const activeCount = document.getElementById('active-count');
            const activeList = document.getElementById('active-list');
            if (activeCount) activeCount.textContent = `(${data.active_count})`;
            if (activeList) {
                let html = '';
                if (data.active_connections.length === 0) {
                    html = 'No established connections found.';
                } else {
                    html += 'IP Address'.padEnd(22) + 'Protocol'.padEnd(10) + 'Type'.padEnd(15) + 'Process\n';
                    data.active_connections.forEach(item => {
                        let ip = (item.ip + ':' + item.port).padEnd(22);
                        html += `${ip}${item.protocol.padEnd(10)}${item.type.padEnd(15)}${item.process}\n`;
                    });
                }
                activeList.textContent = html;
            }

            const trafficLog = document.getElementById('traffic-log-list');
            if (trafficLog) {
                let html = '';
                if (data.live_traffic_log.length === 0) {
                    html = '<div class="traffic-entry">Monitoring for new connections...</div>';
                } else {
                    data.live_traffic_log.forEach(item => {
                        html += `<div class="traffic-entry">` +
                            `<span class="timestamp">${item.timestamp.padEnd(15)}</span>` +
                            `<span class="type ${item.type}">${item.type.padEnd(10)}</span>` +
                            `<span class="ip">${item.ip_port.padEnd(26)}</span>` +
                            `<span class="protocol">${item.protocol.padEnd(10)}</span>` +
                            `<span class="process">${item.process}</span>` +
                            `</div>`;
                    });
                }
                trafficLog.innerHTML = html;
                trafficLog.scrollTop = trafficLog.scrollHeight;
            }
        } catch (e) {
            console.error('Failed to update Network UI:', e);
        }
    },

    async savePositions() {
        const positions = {};
        document.querySelectorAll('.widget-container').forEach(container => {
            positions[container.id] = {
                top: container.style.top,
                left: container.style.left,
                right: container.style.right,
                width: container.style.width,
                height: container.style.height
            };
        });

        try {
            await fetch('/save_widget_positions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(positions)
            });
            console.log('Widget positions saved');
        } catch (e) {
            console.error('Error saving positions:', e);
        }
    },

    async restorePositions() {
        const defaultPositions = {
            "live-clock": { "top": "72px", "left": "1709px", "right": "auto", "width": "778px", "height": "181px" },
            "traffic-data": { "top": "1072px", "left": "31px", "right": "auto", "width": "432px", "height": "252px" },
            "listening-ports": { "top": "36px", "left": "36px", "right": "auto", "width": "425px", "height": "995px" },
            "live-traffic-log": { "top": "891px", "left": "1809px", "right": "auto", "width": "683px", "height": "477px" },
            "active-connections": { "top": "299px", "left": "1813px", "right": "auto", "width": "675px", "height": "572px" }
        };

        try {
            const response = await fetch('/widget.json');
            if (response.ok) {
                const positions = await response.json();
                if (positions && Object.keys(positions).length > 0) {
                    Object.keys(positions).forEach(id => {
                        const el = document.getElementById(id);
                        if (el) {
                            const pos = positions[id];
                            if (pos.top) el.style.top = pos.top;
                            if (pos.left) el.style.left = pos.left;
                            if (pos.right) el.style.right = pos.right;
                            if (pos.width) el.style.width = pos.width;
                            if (pos.height) el.style.height = pos.height;
                            if (pos.right && pos.left === 'auto') {
                                el.style.left = 'auto';
                            } else {
                                el.style.right = 'auto';
                            }
                        }
                    });
                    console.log('Widget positions restored');
                    return;
                }
            }
        } catch (e) { }

        Object.keys(defaultPositions).forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                const pos = defaultPositions[id];
                el.style.top = pos.top;
                el.style.left = pos.left;
                el.style.right = pos.right;
                el.style.width = pos.width;
                el.style.height = pos.height;
            }
        });
    },

    isDraggable: false,
    activeContainer: null,
    offsetX: 0,
    offsetY: 0,
    isResizing: false,
    originalWidth: 0,
    originalHeight: 0,
    originalMouseX: 0,
    originalMouseY: 0,

    initDraggableSystem() {
        document.querySelectorAll('.widget-container').forEach(container => {
            container.addEventListener('dblclick', (e) => this.onContainerDoubleClick(e));
            container.addEventListener('mousedown', (e) => this.onContainerMouseDown(e));
        });
        document.querySelectorAll('.resize-handle').forEach(handle => {
            handle.addEventListener('mousedown', (e) => this.onResizeMouseDown(e));
        });
        const bgCatcher = document.getElementById('background-click-catcher');
        if (bgCatcher) {
            bgCatcher.addEventListener('click', () => this.exitEditMode());
        }
    },

    onContainerDoubleClick(e) {
        const container = e.target.closest('.widget-container');
        if (container && !this.isDraggable) {
            this.isDraggable = true;
            document.body.classList.add('is-dragging');
            this.updateCheckboxStates();
            console.log('Edit Mode ENABLED');
        } else if (this.isDraggable) {
            this.exitEditMode();
        }
    },

    onContainerMouseDown(e) {
        if (!this.isDraggable || e.target.classList.contains('resize-handle')) return;
        e.preventDefault();
        this.activeContainer = e.target.closest('.widget-container');
        const rect = this.activeContainer.getBoundingClientRect();
        this.offsetX = e.clientX - rect.left;
        this.offsetY = e.clientY - rect.top;

        const onDragMove = (e) => {
            if (!this.activeContainer) return;
            this.activeContainer.style.left = `${e.clientX - this.offsetX}px`;
            this.activeContainer.style.top = `${e.clientY - this.offsetY}px`;
            this.activeContainer.style.right = 'auto';
        };

        const onDragEnd = () => {
            this.activeContainer = null;
            window.removeEventListener('mousemove', onDragMove);
            window.removeEventListener('mouseup', onDragEnd);
        };

        window.addEventListener('mousemove', onDragMove);
        window.addEventListener('mouseup', onDragEnd);
    },

    onResizeMouseDown(e) {
        if (!this.isDraggable) return;
        e.preventDefault();
        e.stopPropagation();
        this.isResizing = true;
        this.activeContainer = e.target.closest('.widget-container');
        const rect = this.activeContainer.getBoundingClientRect();
        this.originalWidth = rect.width;
        this.originalHeight = rect.height;
        this.originalMouseX = e.clientX;
        this.originalMouseY = e.clientY;

        const onResizeDrag = (e) => {
            if (!this.isResizing || !this.activeContainer) return;
            const deltaX = e.clientX - this.originalMouseX;
            const deltaY = e.clientY - this.originalMouseY;
            this.activeContainer.style.width = `${this.originalWidth + deltaX}px`;
            this.activeContainer.style.height = `${this.originalHeight + deltaY}px`;
        };

        const onResizeEnd = () => {
            this.isResizing = false;
            this.activeContainer = null;
            window.removeEventListener('mousemove', onResizeDrag);
            window.removeEventListener('mouseup', onResizeEnd);
        };

        window.addEventListener('mousemove', onResizeDrag);
        window.addEventListener('mouseup', onResizeEnd);
    },

    updateCheckboxStates() {
        document.querySelectorAll('#edit-mode-menu input[type="checkbox"]').forEach(checkbox => {
            const widgetId = checkbox.getAttribute('data-widget');
            if (widgetId && this.visibility.hasOwnProperty(widgetId)) {
                checkbox.checked = this.visibility[widgetId];
            }
        });
    },

    exitEditMode() {
        if (this.isDraggable) {
            this.isDraggable = false;
            document.body.classList.remove('is-dragging');
            this.savePositions();
            this.saveVisibility();
            console.log('Edit Mode DISABLED. Saved.');
        }
    },

    enterEditMode() {
        if (!this.isDraggable) {
            this.isDraggable = true;
            document.body.classList.add('is-dragging');
            this.updateCheckboxStates();

            const editMenu = document.getElementById('edit-mode-menu');
            if (editMenu) {
                editMenu.style.left = '50%';
                editMenu.style.top = '50%';
                editMenu.style.transform = 'translate(-50%, -50%)';
            }

            console.log('Edit Mode ENABLED via external call.');
        }
    },

    initEditMenu() {
        const closeBtn = document.getElementById('close-edit-menu');
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.exitEditMode();
            });
        }

        const editMenu = document.getElementById('edit-mode-menu');
        if (editMenu) {
            editMenu.addEventListener('dblclick', (e) => e.stopPropagation());
        }

        const dragHandle = document.getElementById('edit-menu-drag-handle');
        if (dragHandle && editMenu) {
            let isMenuDragging = false;
            let menuOffsetX = 0, menuOffsetY = 0;

            dragHandle.addEventListener('mousedown', (e) => {
                if (e.target.closest('.edit-menu-close')) return;
                isMenuDragging = true;
                const rect = editMenu.getBoundingClientRect();
                menuOffsetX = e.clientX - rect.left;
                menuOffsetY = e.clientY - rect.top;
                editMenu.style.transform = 'none';
                editMenu.style.left = rect.left + 'px';
                editMenu.style.top = rect.top + 'px';
                e.preventDefault();
            });

            window.addEventListener('mousemove', (e) => {
                if (!isMenuDragging) return;
                editMenu.style.left = (e.clientX - menuOffsetX) + 'px';
                editMenu.style.top = (e.clientY - menuOffsetY) + 'px';
            });

            window.addEventListener('mouseup', () => {
                isMenuDragging = false;
            });
        }
    },

    contextMenuWidgetId: null,

    initContextMenu() {
        const ctxMenu = document.getElementById('widget-context-menu');
        const editBtn = document.getElementById('ctx-edit-widget');
        const removeBtn = document.getElementById('ctx-remove-widget');

        if (!ctxMenu) return;

        document.addEventListener('click', (e) => {
            if (!e.target.closest('#widget-context-menu')) {
                this.hideContextMenu();
            }
        });

        if (editBtn) {
            editBtn.addEventListener('click', () => {
                if (this.contextMenuWidgetId) {
                    this.openSettingsEditor(this.contextMenuWidgetId);
                }
                this.hideContextMenu();
            });
        }

        if (removeBtn) {
            removeBtn.addEventListener('click', () => {
                if (this.contextMenuWidgetId) {
                    const containerId = this.contextMenuWidgetId === 'clock' ? 'live-clock' : this.contextMenuWidgetId;
                    this.toggleVisibility(containerId, false);
                    this.saveVisibility();
                }
                this.hideContextMenu();
            });
        }
    },

    showContextMenu(widgetId, x, y) {
        const ctxMenu = document.getElementById('widget-context-menu');
        const editBtn = document.getElementById('ctx-edit-widget');
        if (!ctxMenu) return;

        this.contextMenuWidgetId = widgetId;

        const widget = this.loadedWidgets[widgetId];
        const hasEditableSettings = widget?.editableSettings && widget.editableSettings.length > 0;

        if (editBtn) {
            editBtn.style.display = hasEditableSettings ? 'flex' : 'none';
        }

        ctxMenu.style.left = x + 'px';
        ctxMenu.style.top = y + 'px';
        ctxMenu.style.display = 'block';

        const rect = ctxMenu.getBoundingClientRect();
        if (rect.right > window.innerWidth) {
            ctxMenu.style.left = (x - rect.width) + 'px';
        }
        if (rect.bottom > window.innerHeight) {
            ctxMenu.style.top = (y - rect.height) + 'px';
        }
    },

    hideContextMenu() {
        const ctxMenu = document.getElementById('widget-context-menu');
        if (ctxMenu) {
            ctxMenu.style.display = 'none';
            this.contextMenuWidgetId = null;
        }
    },

    settingsWidgetId: null,
    widgetStyles: {},

    async loadWidgetStyles() {
        try {
            const response = await fetch('/widget_styles.json');
            if (response.ok) {
                this.widgetStyles = await response.json();
                console.log('Loaded widget styles:', this.widgetStyles);
            } else {
                console.warn('Failed to load widget styles, using defaults');
                this.widgetStyles = {};
            }
        } catch (e) {
            console.error('Error loading widget styles:', e);
            this.widgetStyles = {};
        }
    },

    getStyles(widgetId) {
        return this.widgetStyles[widgetId] || {};
    },

    async saveStyles(widgetId, data) {
        this.widgetStyles[widgetId] = data;
        try {
            await fetch('/save_widget_styles', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.widgetStyles)
            });
        } catch (e) {
            console.error('Failed to save widget styles:', e);
        }
    },

    openSettingsEditor(widgetId) {
        const editor = document.getElementById('widget-settings-editor');
        const titleEl = document.getElementById('settings-editor-title');
        const contentEl = document.getElementById('settings-editor-content');

        if (!editor || !contentEl) return;

        this.settingsWidgetId = widgetId;

        const widgetInfo = this.registry.find(w => w.id === widgetId);
        const widgetName = widgetInfo ? widgetInfo.name : widgetId;

        if (titleEl) titleEl.textContent = `${widgetName} Settings`;

        const widget = this.loadedWidgets[widgetId];
        const editableSettings = widget?.editableSettings || [];

        const savedStyles = this.getStyles(widgetId);

        if (editableSettings.length === 0) {
            contentEl.innerHTML = '<div class="settings-no-options">No editable settings for this widget</div>';
        } else {
            contentEl.innerHTML = '';
            editableSettings.forEach(setting => {
                const currentValue = savedStyles[setting.key] !== undefined ? savedStyles[setting.key] : setting.value;
                const fieldHtml = this.renderSettingField(setting, currentValue);
                contentEl.innerHTML += fieldHtml;
            });

            contentEl.querySelectorAll('input[type="range"]').forEach(slider => {
                const valueSpan = slider.parentElement.querySelector('.settings-slider-value');
                if (valueSpan) {
                    slider.addEventListener('input', () => {
                        valueSpan.textContent = slider.value + '%';
                    });
                }
            });
        }

        editor.style.display = 'block';
    },

    renderSettingField(setting, currentValue) {
        const { key, label, type, min, max } = setting;
        let inputHtml = '';

        switch (type) {
            case 'string':
                inputHtml = `<input type="text" class="settings-input" data-key="${key}" value="${currentValue || ''}">`;
                break;
            case 'integer':
                inputHtml = `<input type="number" class="settings-input" data-key="${key}" value="${currentValue || 0}">`;
                break;
            case 'slider':
                const minVal = min || 0;
                const maxVal = max || 100;
                inputHtml = `
                    <div class="settings-slider-container">
                        <input type="range" class="settings-input" data-key="${key}" min="${minVal}" max="${maxVal}" value="${currentValue || 50}">
                        <span class="settings-slider-value">${currentValue || 50}%</span>
                    </div>`;
                break;
            case 'color':
                inputHtml = `<input type="color" class="settings-input" data-key="${key}" value="${currentValue || '#ffffff'}">`;
                break;
            case 'select':
                const options = setting.options || [];
                const optionsHtml = options.map(opt => {
                    const optValue = typeof opt === 'object' ? opt.value : opt;
                    const optLabel = typeof opt === 'object' ? opt.label : opt;
                    const selected = optValue === currentValue ? 'selected' : '';
                    return `<option value="${optValue}" ${selected}>${optLabel}</option>`;
                }).join('');
                inputHtml = `<select class="settings-input settings-select" data-key="${key}">${optionsHtml}</select>`;
                break;
            default:
                inputHtml = `<input type="text" class="settings-input" data-key="${key}" value="${currentValue || ''}">`;
        }

        return `
            <div class="settings-field">
                <label class="settings-label">${label}</label>
                ${inputHtml}
            </div>
        `;
    },

    gatherSettingsValues() {
        const contentEl = document.getElementById('settings-editor-content');
        if (!contentEl) return {};

        const values = {};
        contentEl.querySelectorAll('.settings-input').forEach(input => {
            const key = input.getAttribute('data-key');
            if (key) {
                if (input.type === 'number') {
                    values[key] = parseInt(input.value, 10);
                } else if (input.type === 'range') {
                    values[key] = parseInt(input.value, 10);
                } else {
                    values[key] = input.value;
                }
            }
        });
        return values;
    },

    applySettings() {
        if (!this.settingsWidgetId) return;

        const values = this.gatherSettingsValues();
        const widget = this.loadedWidgets[this.settingsWidgetId];

        if (widget && typeof widget.updateStyle === 'function') {
            widget.updateStyle(values);
        }

        this.saveStyles(this.settingsWidgetId, values);
    },

    closeSettingsEditor() {
        const editor = document.getElementById('widget-settings-editor');
        if (editor) {
            editor.style.display = 'none';
            this.settingsWidgetId = null;
        }
    },

    initSettingsEditor() {
        const closeBtn = document.getElementById('close-settings-editor');
        const applyBtn = document.getElementById('settings-apply-btn');
        const okBtn = document.getElementById('settings-ok-btn');
        const editor = document.getElementById('widget-settings-editor');
        const dragHandle = document.getElementById('settings-editor-drag-handle');

        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeSettingsEditor());
        }

        if (applyBtn) {
            applyBtn.addEventListener('click', () => this.applySettings());
        }

        if (okBtn) {
            okBtn.addEventListener('click', () => {
                this.applySettings();
                this.closeSettingsEditor();
            });
        }

        if (editor && dragHandle) {
            let isSettingsDragging = false;
            let settingsOffsetX = 0, settingsOffsetY = 0;

            dragHandle.addEventListener('mousedown', (e) => {
                if (e.target.closest('.settings-editor-close')) return;
                isSettingsDragging = true;
                const rect = editor.getBoundingClientRect();
                settingsOffsetX = e.clientX - rect.left;
                settingsOffsetY = e.clientY - rect.top;
                editor.style.transform = 'none';
                editor.style.left = rect.left + 'px';
                editor.style.top = rect.top + 'px';
                e.preventDefault();
            });

            window.addEventListener('mousemove', (e) => {
                if (!isSettingsDragging) return;
                editor.style.left = (e.clientX - settingsOffsetX) + 'px';
                editor.style.top = (e.clientY - settingsOffsetY) + 'px';
            });

            window.addEventListener('mouseup', () => {
                isSettingsDragging = false;
            });
        }
    }
};

window.WidgetLoader = WidgetLoader;
window.enterEditMode = () => WidgetLoader.enterEditMode();
window.exitEditMode = () => WidgetLoader.exitEditMode();

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => WidgetLoader.init());
} else {
    WidgetLoader.init();
}