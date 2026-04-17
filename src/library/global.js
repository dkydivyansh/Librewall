const WidgetLoader = {
  registry: [],
  loadedWidgets: {},
  visibility: {},
  wsPort: null,
  networkEnabled: false,
  idMap: {
    "3": "live-clock",
    "4": "traffic-data",
    "5": "listening-ports",
    "6": "live-traffic-log",
    "7": "active-connections",
    clock: "live-clock", // Legacy support
  },
  getContainerId(id) {
    const safeId = String(id);
    return this.idMap[safeId] || safeId;
  },

  async loadRegistry() {
    try {
      const response = await fetch("/widgets/index.json");
      if (!response.ok) throw new Error("Registry not found");
      const data = await response.json();
      this.registry = data.widgets || [];
      console.log(`Widget registry loaded: ${this.registry.length} widgets`);
      return this.registry;
    } catch (e) {
      console.error("Failed to load widget registry:", e);
      return [];
    }
  },

  async loadWidget(widgetInfo) {
    const { id } = widgetInfo;
    const safeId = String(id);
    const folder = safeId;

    try {
      const cssPath = `/widgets/${folder}/style.css`;
      if (!document.querySelector(`link[href="${cssPath}"]`)) {
        const link = document.createElement("link");
        link.rel = "stylesheet";
        link.href = cssPath;
        link.id = `widget-css-${safeId}`;
        document.head.appendChild(link);
      }

      const jsPath = `/widgets/${folder}/main.js`;
      const module = await import(jsPath);
      const WidgetClass = module.default;

      if (WidgetClass) {
        widgetInfo.status = "loaded";
        return WidgetClass;
      } else {
        widgetInfo.status = "error";
        return null;
      }
    } catch (e) {
      console.error(`Failed to load widget ${id}:`, e);
      widgetInfo.status = "missing";
      return null;
    }
  },

  applyPosition(containerId, container) {
    try {
      if (this.positionCache && this.positionCache[containerId]) {
        const pos = this.positionCache[containerId];
        if (pos.top) container.style.top = pos.top;
        if (pos.left) container.style.left = pos.left;
        if (pos.right) container.style.right = pos.right;
        if (pos.width) container.style.width = pos.width;
        if (pos.height) container.style.height = pos.height;
        if (pos.right && pos.left === "auto") {
          container.style.left = "auto";
        } else {
          container.style.right = "auto";
        }
      }
    } catch (e) {}
  },

  renderWidget(id, WidgetClass, wrapper) {
    const containerId = this.getContainerId(id);

    let container = document.getElementById(containerId);
    if (!container) {
      container = document.createElement("div");
      container.id = containerId;
      container.className = "widget-container";
      wrapper.appendChild(container);
    }

    const instance = new WidgetClass(id);
    this.loadedWidgets[id] = instance;

    if (instance.settings) {
      if (instance.settings.minWidth) {
        container.style.minWidth = instance.settings.minWidth;
      }
      if (instance.settings.minHeight) {
        container.style.minHeight = instance.settings.minHeight;
      }
      if (instance.settings.transparent === true) {
        container.style.backgroundColor = "transparent";
        container.style.backdropFilter = "none";
        container.style.boxShadow = "none";
        container.style.border = "none";
      }
      if (instance.settings.fixedSize === true) {
        container.classList.add("is-fixed-size");
        container.style.width = "fit-content";
        container.style.height = "fit-content";
        container.style.minWidth = "0";
        container.style.minHeight = "0";
      } else {
        container.classList.remove("is-fixed-size");
      }
    }

    container.innerHTML = instance.html + '<div class="resize-handle"></div>';

    container.addEventListener("mousedown", (e) =>
      this.onContainerMouseDown(e),
    );
    const handle = container.querySelector(".resize-handle");
    if (handle) {
      handle.addEventListener("mousedown", (e) => this.onResizeMouseDown(e));
    }

    container.addEventListener("click", (e) => {
      if (this.isDraggable && e.button === 0) {
        if (this.hasMovedDuringDrag) return;
        if (e.target.closest("button, input, a, canvas, .resize-handle"))
          return;
        this.showContextMenu(id, e.clientX, e.clientY);
        e.stopPropagation();
      }
    });

    if (typeof this.applyPosition === "function") {
      this.applyPosition(containerId, container);
    }

    if (typeof instance.init === "function") {
      instance.init();
    }

    return container;
  },

  unloadWidget(id) {
    const widget = this.loadedWidgets[id];
    if (widget && typeof widget.destroy === "function") {
      widget.destroy();
    }

    const containerId = this.getContainerId(id);
    const container = document.getElementById(containerId);
    if (container) {
      container.remove();
    }

    const cssLink = document.getElementById(`widget-css-${id}`);
    if (cssLink) cssLink.remove();

    delete this.loadedWidgets[id];
  },

  async savePositions() {
    const positions = {};
    document.querySelectorAll(".widget-container").forEach((el) => {
      positions[el.id] = {
        left: el.style.left,
        top: el.style.top,
      };
    });

    try {
      const response = await fetch("/save_widget_positions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(positions),
      });
      if (response.ok) console.log("Positions saved");
    } catch (e) {
      console.error("Error saving positions:", e);
    }
  },

  positionCache: {},

  async saveVisibility() {
    try {
      const response = await fetch("/save_widget_visibility", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.visibility),
      });
      if (response.ok) console.log("Widget visibility saved");
    } catch (e) {
      console.error("Error saving visibility:", e);
    }
  },

  async restoreVisibility() {
    let hasVisibilityConfig = false;
    try {
      const response = await fetch("/widget_visibility.json");
      if (response.ok) {
        this.visibility = await response.json();
        hasVisibilityConfig = Object.keys(this.visibility).length > 0;
      }
    } catch (e) {}

    this.registry.forEach((w) => {
      const containerId = this.getContainerId(w.id);

      if (this.visibility[containerId] === undefined) {
        if (!hasVisibilityConfig && containerId === "live-clock") {
          this.visibility[containerId] = true;
        } else {
          this.visibility[containerId] = false;
        }
      }
    });

    if (!hasVisibilityConfig) {
      this.saveVisibility();
    }
  },

  async toggleVisibility(widgetId, visible) {
    const containerId = this.getContainerId(widgetId);
    this.visibility[containerId] = visible;

    if (visible) {
      if (this.loadedWidgets[widgetId]) {
        const el = document.getElementById(containerId);
        if (el) {
          el.style.display = "";
          if (typeof this.applyPosition === "function")
            this.applyPosition(containerId, el);
        }
        return;
      }
      const widgetInfo = this.registry.find((w) => w.id === widgetId);
      if (!widgetInfo) return;

      const WidgetClass = await this.loadWidget(widgetInfo);
      if (WidgetClass) {
        const wrapper = document.getElementById("widget-wrapper");
        this.renderWidget(widgetId, WidgetClass, wrapper);
      }
    } else {
      this.unloadWidget(widgetId);
    }
  },

  async init() {
    console.log("Librewall Script starting...");
    this.showLoading();
    await this.loadRegistry();
    await this.loadWidgetStyles();

    const wrapper = document.getElementById("widget-wrapper");
    if (!wrapper) {
      console.error("widget-wrapper not found");
      return;
    }

    try {
      const configResponse = await fetch("/config");
      const config = await configResponse.json();
      this.networkEnabled =
        config.Enable_Global_Widget === true ||
        config.Enable_Network_Widget === true;
    } catch (e) {}

    this.registry = this.registry.filter((w) => w.status !== "missing");

    await this.restorePositions();
    await this.restoreVisibility();

    if (this.networkEnabled) {
      await this.initNetworkConnection();
    }

    await Promise.all(
      this.registry.map(async (widgetInfo) => {
        const containerId = this.getContainerId(widgetInfo.id);
        if (this.visibility[containerId]) {
          await this.toggleVisibility(widgetInfo.id, true);
        }
      }),
    );

    this.initDraggableSystem();
    this.initEditMenu();
    this.initContextMenu();
    this.initSettingsEditor();
    this.initTemplateManager();
    await this.populateEditMenu();
    this.initWidgetSearch();

    setTimeout(() => this.hideLoading(), 500);
  },

  showLoading() {
    const overlay = document.getElementById("loading-overlay");
    if (overlay) {
      overlay.style.opacity = "1";
      overlay.style.pointerEvents = "all";
    }
  },

  hideLoading() {
    const overlay = document.getElementById("loading-overlay");
    if (overlay) {
      overlay.style.opacity = "0";
      overlay.style.pointerEvents = "none";

      setTimeout(() => {}, 500);
    }
  },

  setupWidgetClickHandlers() {
    document.querySelectorAll(".widget-container").forEach((container) => {
      container.addEventListener("click", (e) => {
        if (this.isDraggable && e.button === 0) {
          if (this.hasMovedDuringDrag) return;
          if (e.target.closest("button, input, a, canvas, .resize-handle"))
            return;

          let widgetId = container.id;
          // Reverse lookup or use original ID if possible?
          // Since we use descriptive IDs for containers, let's find the original widget ID
          const entry = Object.entries(this.idMap).find(([k, v]) => v === widgetId);
          const finalId = entry ? entry[0] : widgetId;

          this.showContextMenu(finalId, e.clientX, e.clientY);
          e.stopPropagation();
        }
      });
    });
  },

  async populateEditMenu() {
    const list = document.getElementById("widget-toggle-list");
    if (!list) return;

    list.innerHTML = "";

    await Promise.all(
      this.registry.map(async (w) => {
        if (w._hasSettings === undefined) {
          try {
            const folder = String(w.id);
            const res = await fetch(`/widgets/${folder}/main.js`);
            const text = await res.text();
            w._hasSettings = text.includes("editableSettings");
          } catch (e) {
            w._hasSettings = false;
          }
        }
      }),
    );

    this.registry.forEach((w) => {
      const containerId = this.getContainerId(w.id);
      const checked = this.visibility[containerId] !== false ? "checked" : "";

      const isError = w.status === "error" || w.status === "missing";
      const hasSettings = w._hasSettings !== false;

      const label = document.createElement("label");
      label.className = "widget-toggle";

      if (isError) {
        label.style.backgroundColor = "rgba(255, 68, 68, 0.1)";
        label.style.border = "1px solid rgba(255, 68, 68, 0.3)";
        label.style.borderRadius = "8px";
        label.style.marginBottom = "5px";
      }

      label.innerHTML = `
                <input type="checkbox" data-widget="${w.id}" data-container-id="${containerId}" ${checked} ${isError ? "disabled" : ""}>
                <span ${isError ? 'style="color: #ffaa99;"' : ""}>${w.name}</span>
                ${
                  isError
                    ? `
                <span class="widget-error-icon" title="Corrupted or Missing" style="color: #ff4444; margin-left: auto; display: flex; align-items: center;">
                    <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" fill="currentColor" height="20px" width="20px" version="1.1" viewBox="0 0 512.018 512.018" xml:space="preserve">
                        <g><path d="M509.769,480.665L275.102,11.331c-7.253-14.464-30.933-14.464-38.187,0L2.249,480.665c-3.307,6.613-2.944,14.464,0.939,20.757c3.904,6.272,10.752,10.112,18.155,10.112h469.333c7.403,0,14.251-3.84,18.155-10.112C512.713,495.129,513.075,487.278,509.769,480.665z M256.009,426.201c-11.776,0-21.333-9.557-21.333-21.333s9.557-21.333,21.333-21.333s21.333,9.557,21.333,21.333S267.785,426.201,256.009,426.201z M277.342,340.867c0,11.776-9.536,21.333-21.333,21.333c-11.797,0-21.333-9.557-21.333-21.333V191.534c0-11.776,9.536-21.333,21.333-21.333c11.797,0,21.333,9.557,21.333,21.333V340.867z"/></g>
                    </svg>
                </span>`
                    : ""
                }
                ${
                  !isError && hasSettings
                    ? `
                <button class="widget-edit-btn" data-widget-id="${w.id}" title="Edit Settings">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="3"/>
                        <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>
                    </svg>
                </button>
                `
                    : ""
                }
            `;
      list.appendChild(label);
    });

    list.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
      checkbox.addEventListener("change", async (e) => {
        const widgetId = e.target.getAttribute("data-widget");
        if (widgetId) {
          e.target.disabled = true;
          e.target.style.opacity = "0.5";
          try {
            await this.toggleVisibility(widgetId, e.target.checked);
            this.saveVisibility();

            const wInfo = this.registry.find((w) => String(w.id) === widgetId);
            if (
              wInfo &&
              (wInfo.status === "error" || wInfo.status === "missing")
            ) {
              e.target.checked = false;
              this.populateEditMenu();
            }
          } catch (err) {
            console.error(err);
            e.target.checked = !e.target.checked;
          }
          e.target.disabled = false;
          e.target.style.opacity = "1";
        }
      });
    });

    list.querySelectorAll(".widget-edit-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const widgetId = btn.getAttribute("data-widget-id");
        this.openSettingsEditor(widgetId);
      });
    });
  },

  initWidgetSearch() {
    const searchInput = document.getElementById("widget-search");
    if (!searchInput) return;

    searchInput.addEventListener("input", (e) => {
      const query = e.target.value.toLowerCase().trim();
      const toggles = document.querySelectorAll(".widget-toggle");

      toggles.forEach((toggle) => {
        const name =
          toggle.querySelector("span")?.textContent.toLowerCase() || "";
        toggle.style.display = name.includes(query) ? "flex" : "none";
      });
    });
  },

  async initNetworkConnection() {
    try {
      const appConfigResponse = await fetch("/app_config.json");
      const appConfig = await appConfigResponse.json();
      this.wsPort = appConfig.ws_port;

      if (this.wsPort) {
        this.connectWebSocket(this.wsPort);
      }
    } catch (e) {
      console.error("Failed to init network connection:", e);
    }
  },

  connectWebSocket(port) {
    const socket = new WebSocket(`ws://localhost:${port}`);

    socket.onopen = () => {
      console.log("WebSocket connected");
    };

    socket.onmessage = (event) => {
      this.updateNetworkUI(JSON.parse(event.data));
    };

    socket.onclose = () => {
      setTimeout(() => this.connectWebSocket(port), 3000);
    };

    socket.onerror = () => {};
  },

  formatBits(bits, perSecond = false) {
    if (!bits || bits === 0) return "0 " + (perSecond ? "bps" : "b");
    const k = 1000;
    const sizes = perSecond
      ? ["bps", "Kbps", "Mbps", "Gbps", "Tbps"]
      : ["b", "Kb", "Mb", "Gb", "Tb"];
    const i = Math.floor(Math.log(bits) / Math.log(k));
    return `${parseFloat((bits / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  },

  formatBytes(bytes) {
    if (!bytes || bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  },

  updateNetworkUI(data) {
    try {
      const uploadEl = document.getElementById("upload-speed");
      const downloadEl = document.getElementById("download-speed");
      const totalSentEl = document.getElementById("total-sent");
      const totalRecvEl = document.getElementById("total-recv");

      if (uploadEl)
        uploadEl.textContent = this.formatBits(data.upload_bps, true);
      if (downloadEl)
        downloadEl.textContent = this.formatBits(data.download_bps, true);
      if (totalSentEl)
        totalSentEl.textContent = this.formatBytes(data.total_sent);
      if (totalRecvEl)
        totalRecvEl.textContent = this.formatBytes(data.total_recv);

      const listeningCount = document.getElementById("listening-count");
      const listeningList = document.getElementById("listening-ports-list");
      if (listeningCount)
        listeningCount.textContent = `(${data.listening_count})`;
      if (listeningList) {
        if (data.listening_ports.length === 0) {
          listeningList.innerHTML =
            '<div class="net-entry">No listening ports found.</div>';
        } else {
          listeningList.innerHTML = data.listening_ports
            .map(
              (item) =>
                `<div class="net-entry"><span class="net-cell net-port">${item.port} (${item.protocol})</span><span class="net-cell net-process">${item.process}</span></div>`,
            )
            .join("");
        }
      }

      const activeCount = document.getElementById("active-count");
      const activeList = document.getElementById("active-list");
      if (activeCount) activeCount.textContent = `(${data.active_count})`;
      if (activeList) {
        if (data.active_connections.length === 0) {
          activeList.innerHTML =
            '<div class="net-entry">No established connections found.</div>';
        } else {
          activeList.innerHTML = data.active_connections
            .map(
              (item) =>
                `<div class="net-entry"><span class="net-cell net-ip">${item.ip}:${item.port}</span><span class="net-cell net-protocol">${item.protocol}</span><span class="net-cell net-process">${item.process}</span></div>`,
            )
            .join("");
        }
      }

      const trafficLog = document.getElementById("traffic-log-list");
      if (trafficLog) {
        if (data.live_traffic_log.length === 0) {
          trafficLog.innerHTML =
            '<div class="traffic-entry">Monitoring for new connections...</div>';
        } else {
          // Dynamically adjust limit based on visible container height
          const estimatedLineHeight = 16;
          const maxVisible =
            Math.ceil(trafficLog.clientHeight / estimatedLineHeight) + 2;
          const visibleLogs = data.live_traffic_log.slice(-maxVisible);

          trafficLog.innerHTML = visibleLogs
            .map(
              (item) =>
                `<div class="net-entry ${item.category}"><span class="net-cell net-timestamp">${item.timestamp}</span><span class="net-cell net-port">${item.ip_port}</span><span class="net-cell net-protocol">${item.protocol}</span><span class="net-cell net-process">${item.process}</span></div>`,
            )
            .join("");
        }
        trafficLog.scrollTop = trafficLog.scrollHeight;
      }
    } catch (e) {
      console.error("Failed to update Network UI:", e);
    }
  },

  async savePositions() {
    if (!this.positionCache) this.positionCache = {};

    document.querySelectorAll(".widget-container").forEach((container) => {
      this.positionCache[container.id] = {
        top: container.style.top,
        left: container.style.left,
        right: container.style.right,
        width: container.style.width,
        height: container.style.height,
      };
    });

    try {
      await fetch("/save_widget_positions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.positionCache),
      });
      console.log("Widget positions saved");
    } catch (e) {
      console.error("Error saving positions:", e);
    }
  },
  async restorePositions() {
    this.positionCache = {};
    try {
      const response = await fetch("/widget.json");
      if (response.ok) {
        const positions = await response.json();
        if (positions && Object.keys(positions).length > 0) {
          this.positionCache = positions;

          Object.keys(this.positionCache).forEach((id) => {
            const el = document.getElementById(id);
            if (el) {
              this.applyPosition(id, el);
            }
          });
          console.log("Widget positions restored");
          return;
        }
      }
    } catch (e) {}

    const ww = window.innerWidth;
    const wh = window.innerHeight;

    this.positionCache = {
      "live-clock": {
        top: "72px",
        left: `${Math.max(10, ww - 800)}px`,
        right: "auto",
        width: "778px",
        height: "181px",
      },
      "traffic-data": {
        top: `${Math.max(10, wh - 270)}px`,
        left: "31px",
        right: "auto",
        width: "432px",
        height: "252px",
      },
      "listening-ports": {
        top: "36px",
        left: "36px",
        right: "auto",
        width: "425px",
        height: `${Math.min(995, wh - 100)}px`,
      },
      "live-traffic-log": {
        top: `${Math.max(10, wh - 500)}px`,
        left: `${Math.max(10, ww - 700)}px`,
        right: "auto",
        width: "683px",
        height: "477px",
      },
      "active-connections": {
        top: "299px",
        left: `${Math.max(10, ww - 700)}px`,
        right: "auto",
        width: "675px",
        height: "572px",
      },
    };

    Object.keys(this.positionCache).forEach((id) => {
      const el = document.getElementById(id);
      if (el) {
        this.applyPosition(id, el);
      }
    });
  },

  isDraggable: false,
  activeContainer: null,
  offsetX: 0,
  offsetY: 0,
  hasMovedDuringDrag: false,
  dragStartX: 0,
  dragStartY: 0,
  isResizing: false,
  originalWidth: 0,
  originalHeight: 0,
  originalMouseX: 0,
  originalMouseY: 0,

  initDraggableSystem() {
    const bgCatcher = document.getElementById("background-click-catcher");
    if (bgCatcher) {
      bgCatcher.addEventListener("click", () => this.exitEditMode());
    }
  },

  onContainerMouseDown(e) {
    if (!this.isDraggable || e.target.classList.contains("resize-handle"))
      return;
    e.preventDefault();
    this.activeContainer = e.target.closest(".widget-container");
    const rect = this.activeContainer.getBoundingClientRect();
    this.offsetX = e.clientX - rect.left;
    this.offsetY = e.clientY - rect.top;
    this.dragStartX = e.clientX;
    this.dragStartY = e.clientY;
    this.hasMovedDuringDrag = false;

    const onDragMove = (e) => {
      if (!this.activeContainer) return;

      const dist = Math.sqrt(
        Math.pow(e.clientX - this.dragStartX, 2) +
          Math.pow(e.clientY - this.dragStartY, 2),
      );
      if (dist > 3) {
        this.hasMovedDuringDrag = true;
      }

      this.activeContainer.style.left = `${e.clientX - this.offsetX}px`;
      this.activeContainer.style.top = `${e.clientY - this.offsetY}px`;
      this.activeContainer.style.right = "auto";
    };

    const onDragEnd = () => {
      this.activeContainer = null;
      window.removeEventListener("mousemove", onDragMove);
      window.removeEventListener("mouseup", onDragEnd);
    };

    window.addEventListener("mousemove", onDragMove);
    window.addEventListener("mouseup", onDragEnd);
  },

  onResizeMouseDown(e) {
    if (!this.isDraggable) return;
    e.preventDefault();
    e.stopPropagation();
    this.isResizing = true;
    this.activeContainer = e.target.closest(".widget-container");
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
      window.removeEventListener("mousemove", onResizeDrag);
      window.removeEventListener("mouseup", onResizeEnd);
    };

    window.addEventListener("mousemove", onResizeDrag);
    window.addEventListener("mouseup", onResizeEnd);
  },

  updateCheckboxStates() {
    document
      .querySelectorAll('#edit-mode-menu input[type="checkbox"]')
      .forEach((checkbox) => {
        const widgetId = checkbox.getAttribute("data-widget");
        const containerId = this.getContainerId(widgetId);
        if (widgetId && this.visibility.hasOwnProperty(containerId)) {
          checkbox.checked = this.visibility[containerId];
        }
      });
  },

  exitEditMode() {
    if (this.isDraggable) {
      this.isDraggable = false;
      document.body.classList.remove("is-dragging");

      const editMenu = document.getElementById("edit-mode-menu");
      if (editMenu) {
        editMenu.style.display = "";
      }

      this.savePositions();
      this.saveVisibility();
      console.log("Edit Mode DISABLED. Saved (v2.7).");
    }
  },

  enterEditMode() {
    if (!this.isDraggable) {
      this.isDraggable = true;
      document.body.classList.add("is-dragging");
      this.updateCheckboxStates();

      const editMenu = document.getElementById("edit-mode-menu");
      if (editMenu) {
        this.resetEditMenuPosition();
      }
      console.log("Edit Mode ENABLED via external call (v2.7).");
    }
  },

  resetWindowPosition(id) {
    const el = document.getElementById(id);
    if (!el) return;

    el.style.display = "block";
    el.style.transform = "none";

    const rect = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    const left = Math.max(0, (vw - rect.width) / 2);
    const top = Math.max(0, (vh - rect.height) / 2);

    el.style.left = left + "px";
    el.style.top = top + "px";
  },

  resetEditMenuPosition() {
    this.resetWindowPosition("edit-mode-menu");
  },

  initEditMenu() {
    const closeBtn = document.getElementById("close-edit-menu");
    if (closeBtn) {
      closeBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        this.exitEditMode();
      });
    }

    const editMenu = document.getElementById("edit-mode-menu");
    if (editMenu) {
      editMenu.addEventListener("dblclick", (e) => e.stopPropagation());
    }

    const dragHandle = document.getElementById("edit-menu-drag-handle");
    if (dragHandle && editMenu) {
      let isMenuDragging = false;
      let menuOffsetX = 0,
        menuOffsetY = 0;

      dragHandle.addEventListener("mousedown", (e) => {
        if (e.target.closest(".edit-menu-close")) return;
        isMenuDragging = true;
        const rect = editMenu.getBoundingClientRect();
        menuOffsetX = e.clientX - rect.left;
        menuOffsetY = e.clientY - rect.top;
        editMenu.style.transform = "none";
        editMenu.style.left = rect.left + "px";
        editMenu.style.top = rect.top + "px";
        const onMouseMove = (e) => {
          let newLeft = e.clientX - menuOffsetX;
          let newTop = e.clientY - menuOffsetY;

          const rect = editMenu.getBoundingClientRect();

          newLeft = Math.max(
            0,
            Math.min(newLeft, window.innerWidth - rect.width),
          );
          newTop = Math.max(
            0,
            Math.min(newTop, window.innerHeight - rect.height),
          );

          editMenu.style.left = newLeft + "px";
          editMenu.style.top = newTop + "px";
        };

        const onMouseUp = () => {
          isMenuDragging = false;
          window.removeEventListener("mousemove", onMouseMove);
          window.removeEventListener("mouseup", onMouseUp);
        };

        window.addEventListener("mousemove", onMouseMove);
        window.addEventListener("mouseup", onMouseUp);
      });
    }
  },

  contextMenuWidgetId: null,

  initContextMenu() {
    const ctxMenu = document.getElementById("widget-context-menu");
    const editBtn = document.getElementById("ctx-edit-widget");
    const removeBtn = document.getElementById("ctx-remove-widget");

    if (!ctxMenu) return;

    document.addEventListener("click", (e) => {
      if (!e.target.closest("#widget-context-menu")) {
        this.hideContextMenu();
      }
    });

    if (editBtn) {
      editBtn.addEventListener("click", () => {
        if (this.contextMenuWidgetId) {
          this.openSettingsEditor(this.contextMenuWidgetId);
        }
        this.hideContextMenu();
      });
    }

    if (removeBtn) {
      removeBtn.addEventListener("click", () => {
        if (this.contextMenuWidgetId) {
          const containerId = this.getContainerId(this.contextMenuWidgetId);
          this.toggleVisibility(this.contextMenuWidgetId, false);
          this.saveVisibility();
        }
        this.hideContextMenu();
      });
    }
  },

  showContextMenu(widgetId, x, y) {
    const ctxMenu = document.getElementById("widget-context-menu");
    const editBtn = document.getElementById("ctx-edit-widget");
    if (!ctxMenu) return;

    this.contextMenuWidgetId = widgetId;

    const widget = this.loadedWidgets[widgetId];
    const hasEditableSettings =
      widget?.editableSettings && widget.editableSettings.length > 0;

    if (editBtn) {
      editBtn.style.display = hasEditableSettings ? "flex" : "none";
    }

    ctxMenu.style.left = x + "px";
    ctxMenu.style.top = y + "px";
    ctxMenu.style.display = "block";

    const rect = ctxMenu.getBoundingClientRect();
    if (rect.right > window.innerWidth) {
      ctxMenu.style.left = x - rect.width + "px";
    }
    if (rect.bottom > window.innerHeight) {
      ctxMenu.style.top = y - rect.height + "px";
    }
  },

  hideContextMenu() {
    const ctxMenu = document.getElementById("widget-context-menu");
    if (ctxMenu) {
      ctxMenu.style.display = "none";
      this.contextMenuWidgetId = null;
    }
  },

  settingsWidgetId: null,
  widgetStyles: {},

  async loadWidgetStyles() {
    try {
      const response = await fetch("/widget_styles.json");
      if (response.ok) {
        this.widgetStyles = await response.json();
        console.log("Loaded widget styles:", this.widgetStyles);
      } else {
        console.warn("Failed to load widget styles, using defaults");
        this.widgetStyles = {};
      }
    } catch (e) {
      console.error("Error loading widget styles:", e);
      this.widgetStyles = {};
    }
  },

  getStyles(widgetId) {
    return this.widgetStyles[widgetId] || {};
  },

  async saveStyles(widgetId, data) {
    this.widgetStyles[widgetId] = data;
    try {
      await fetch("/save_widget_styles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.widgetStyles),
      });
    } catch (e) {
      console.error("Failed to save widget styles:", e);
    }
  },

  async openSettingsEditor(widgetId) {
    const editor = document.getElementById("widget-settings-editor");
    const titleEl = document.getElementById("settings-editor-title");
    const contentEl = document.getElementById("settings-editor-content");
    const applyBtn = document.getElementById("settings-apply-btn");

    if (!editor || !contentEl) return;

    this.settingsWidgetId = widgetId;

    const widgetInfo = this.registry.find((w) => w.id === widgetId);
    const widgetName = widgetInfo ? widgetInfo.name : widgetId;

    if (titleEl) titleEl.textContent = `${widgetName} Settings`;

    let widget = this.loadedWidgets[widgetId];
    let isWidgetActive = !!widget;

    if (!isWidgetActive && widgetInfo) {
      const WidgetClass = await this.loadWidget(widgetInfo);
      if (WidgetClass) {
        widget = new WidgetClass(widgetId);
      }
    }

    if (applyBtn) {
      applyBtn.style.display = isWidgetActive ? "" : "none";
    }

    const editableSettings = widget?.editableSettings || [];

    const savedStyles = this.getStyles(widgetId);

    if (editableSettings.length === 0) {
      contentEl.innerHTML =
        '<div class="settings-no-options">No editable settings for this widget</div>';
    } else {
      contentEl.innerHTML = "";
      editableSettings.forEach((setting) => {
        const currentValue =
          savedStyles[setting.key] !== undefined
            ? savedStyles[setting.key]
            : setting.value;
        const fieldHtml = this.renderSettingField(setting, currentValue);
        contentEl.innerHTML += fieldHtml;
      });

      contentEl.querySelectorAll(".settings-input").forEach((input) => {
        if (input.type === "range") {
          const valueSpan = input.parentElement.querySelector(
            ".settings-slider-value",
          );
          if (valueSpan) {
            input.addEventListener("input", () => {
              valueSpan.textContent = input.value + "%";
            });
          }
        }
      });
    }

    this.resetWindowPosition("widget-settings-editor");
  },

  renderSettingField(setting, currentValue) {
    const { key, label, type, min, max } = setting;
    let inputHtml = "";

    switch (type) {
      case "string":
        inputHtml = `<input type="text" class="settings-input" data-key="${key}" value="${currentValue || ""}">`;
        break;
      case "integer":
        inputHtml = `<input type="number" class="settings-input" data-key="${key}" value="${currentValue || 0}">`;
        break;
      case "slider":
        const minVal = min || 0;
        const maxVal = max || 100;
        inputHtml = `
                    <div class="settings-slider-container">
                        <input type="range" class="settings-input" data-key="${key}" min="${minVal}" max="${maxVal}" value="${currentValue || 50}">
                        <span class="settings-slider-value">${currentValue || 50}%</span>
                    </div>`;
        break;
      case "color":
        inputHtml = `<input type="color" class="settings-input" data-key="${key}" value="${currentValue || "#ffffff"}">`;
        break;
      case "boolean":
        const checked = currentValue === true ? "checked" : "";
        inputHtml = `<input type="checkbox" class="settings-input" data-key="${key}" ${checked}>`;
        break;
      case "select":
        const options = setting.options || [];
        const optionsHtml = options
          .map((opt) => {
            const optValue = typeof opt === "object" ? opt.value : opt;
            const optLabel = typeof opt === "object" ? opt.label : opt;
            const selected = optValue === currentValue ? "selected" : "";
            return `<option value="${optValue}" ${selected}>${optLabel}</option>`;
          })
          .join("");
        inputHtml = `<select class="settings-input settings-select" data-key="${key}">${optionsHtml}</select>`;
        break;
      default:
        inputHtml = `<input type="text" class="settings-input" data-key="${key}" value="${currentValue || ""}">`;
    }

    return `
            <div class="settings-field field-type-${type}">
                <label class="settings-label">${label}</label>
                ${inputHtml}
            </div>
        `;
  },

  gatherSettingsValues() {
    const contentEl = document.getElementById("settings-editor-content");
    if (!contentEl) return {};

    const values = {};
    contentEl.querySelectorAll(".settings-input").forEach((input) => {
      const key = input.getAttribute("data-key");
      if (key) {
        if (input.type === "number" || input.type === "range") {
          values[key] = parseInt(input.value, 10);
        } else if (input.type === "checkbox") {
          values[key] = input.checked;
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

    if (values.hasOwnProperty("transparent")) {
      const containerId = this.getContainerId(this.settingsWidgetId);
      const el = document.getElementById(containerId);
      if (el) {
        if (values.transparent === true) {
          el.style.backgroundColor = "transparent";
          el.style.backdropFilter = "none";
          el.style.boxShadow = "none";
          el.style.border = "none";
        } else {
          el.style.backgroundColor = "";
          el.style.backdropFilter = "";
          el.style.boxShadow = "";
          el.style.border = "";
        }
      }
    }

    if (values.hasOwnProperty("fixedSize")) {
      const containerId = this.getContainerId(this.settingsWidgetId);
      const el = document.getElementById(containerId);
      if (el) {
        if (values.fixedSize === true) {
          el.classList.add("is-fixed-size");
          el.style.width = "fit-content";
          el.style.height = "fit-content";
          el.style.minWidth = "0";
          el.style.minHeight = "0";
        } else {
          el.classList.remove("is-fixed-size");
          el.style.width = "";
          el.style.height = "";
          el.style.minWidth = "";
          el.style.minHeight = "";
        }
      }
    }

    if (widget && typeof widget.updateStyle === "function") {
      widget.updateStyle(values);
    }

    this.saveStyles(this.settingsWidgetId, values);
  },

  closeSettingsEditor() {
    const editor = document.getElementById("widget-settings-editor");
    if (editor) {
      editor.style.display = "none";
      this.settingsWidgetId = null;
    }
  },

  initSettingsEditor() {
    const closeBtn = document.getElementById("close-settings-editor");
    const applyBtn = document.getElementById("settings-apply-btn");
    const okBtn = document.getElementById("settings-ok-btn");
    const editor = document.getElementById("widget-settings-editor");
    const dragHandle = document.getElementById("settings-editor-drag-handle");

    if (closeBtn) {
      closeBtn.addEventListener("click", () => this.closeSettingsEditor());
    }

    if (applyBtn) {
      applyBtn.addEventListener("click", () => this.applySettings());
    }

    if (okBtn) {
      okBtn.addEventListener("click", () => {
        this.applySettings();
        this.closeSettingsEditor();
      });
    }

    if (editor && dragHandle) {
      let isSettingsDragging = false;
      let settingsOffsetX = 0,
        settingsOffsetY = 0;

      dragHandle.addEventListener("mousedown", (e) => {
        if (e.target.closest(".settings-editor-close")) return;
        isSettingsDragging = true;
        const rect = editor.getBoundingClientRect();
        settingsOffsetX = e.clientX - rect.left;
        settingsOffsetY = e.clientY - rect.top;
        editor.style.transform = "none";
        editor.style.left = rect.left + "px";
        editor.style.top = rect.top + "px";
        const onMouseMove = (e) => {
          let newLeft = e.clientX - settingsOffsetX;
          let newTop = e.clientY - settingsOffsetY;
          const rect = editor.getBoundingClientRect();

          newLeft = Math.max(
            0,
            Math.min(newLeft, window.innerWidth - rect.width),
          );
          newTop = Math.max(
            0,
            Math.min(newTop, window.innerHeight - rect.height),
          );

          editor.style.left = newLeft + "px";
          editor.style.top = newTop + "px";
        };

        const onMouseUp = () => {
          isSettingsDragging = false;
          window.removeEventListener("mousemove", onMouseMove);
          window.removeEventListener("mouseup", onMouseUp);
        };

        window.addEventListener("mousemove", onMouseMove);
        window.addEventListener("mouseup", onMouseUp);
      });
    }
  },

  async listTemplates() {
    try {
      const res = await fetch("/list_templates");
      const data = await res.json();
      return data.templates || [];
    } catch (e) {
      console.error("Error listing templates:", e);
      return [];
    }
  },

  showNotification(message, type = "info") {
    const popup = document.getElementById("notification-popup");
    const msgEl = document.getElementById("notif-message");
    const iconEl = document.getElementById("notif-icon");
    if (!popup || !msgEl) return;

    msgEl.textContent = message;
    popup.className = `notification-popup show ${type}`;

    if (type === "success") iconEl.innerHTML = "✅";
    else if (type === "error") iconEl.innerHTML = "⚠️";
    else iconEl.innerHTML = "ℹ️";

    setTimeout(() => {
      popup.className = "notification-popup";
    }, 3000);
  },

  confirmAction(message) {
    return new Promise((resolve) => {
      const overlay = document.getElementById("custom-confirm-overlay");
      const msgEl = document.getElementById("confirm-message");
      const okBtn = document.getElementById("confirm-ok-btn");
      const cancelBtn = document.getElementById("confirm-cancel-btn");

      if (!overlay) {
        resolve(confirm(message));
        return;
      }

      msgEl.textContent = message;
      overlay.classList.add("show");

      const cleanup = () => {
        overlay.classList.remove("show");
        okBtn.removeEventListener("click", onOk);
        cancelBtn.removeEventListener("click", onCancel);
      };

      const onOk = () => {
        cleanup();
        resolve(true);
      };
      const onCancel = () => {
        cleanup();
        resolve(false);
      };

      okBtn.addEventListener("click", onOk);
      cancelBtn.addEventListener("click", onCancel);
    });
  },

  async handleSaveTemplate() {
    const input = document.getElementById("template-name-input");
    if (!input || !input.value.trim()) {
      this.showNotification("Please enter a template name", "error");
      return;
    }
    const name = input.value.trim();

    try {
      const res = await fetch("/save_template", {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      if (res.ok) {
        input.value = "";
        this.refreshTemplateList();
        this.showNotification("Template saved successfully", "success");
      } else {
        this.showNotification("Failed to save template", "error");
      }
    } catch (e) {
      console.error(e);
      this.showNotification("Error saving template", "error");
    }
  },

  async handleLoadTemplate(name) {
    const confirmed = await this.confirmAction(
      `Overwrite current layout with template "${name}"?`,
    );
    if (!confirmed) return;

    try {
      const res = await fetch("/load_template", {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      if (res.ok) {
        await this.restorePositions();
        await this.restoreVisibility();
        await this.loadWidgetStyles();
        this.updateCheckboxStates();
        this.showNotification("Template loaded! Reloading...", "success");
        setTimeout(() => location.reload(), 1000);
      } else {
        this.showNotification("Failed to load template", "error");
      }
    } catch (e) {
      console.error(e);
      this.showNotification("Error loading template", "error");
    }
  },

  async handleDeleteTemplate(name) {
    const confirmed = await this.confirmAction(`Delete template "${name}"?`);
    if (!confirmed) return;

    try {
      const res = await fetch("/delete_template", {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      if (res.ok) {
        this.refreshTemplateList();
        this.showNotification("Template deleted", "success");
      } else {
        this.showNotification("Failed to delete template", "error");
      }
    } catch (e) {
      console.error(e);
      this.showNotification("Error deleting template", "error");
    }
  },

  async refreshTemplateList() {
    const list = document.getElementById("template-list");
    if (!list) return;

    const templates = await this.listTemplates();

    if (templates.length === 0) {
      list.innerHTML =
        '<div style="color: #666; font-style: italic; padding: 10px; text-align: center;">No saved templates</div>';
      return;
    }

    list.innerHTML = "";
    templates.forEach((name) => {
      const item = document.createElement("div");
      item.className = "tpl-item";
      item.innerHTML = `
                <span class="tpl-name">${name}</span>
                <div class="tpl-actions">
                    <button class="tpl-btn-icon load" title="Load Template">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 3v12"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <path d="M5 21h14"></path>
                        </svg>
                    </button>
                    <button class="tpl-btn-icon delete" title="Delete Template">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"></path>
                        </svg>
                    </button>
                </div>
            `;

      item
        .querySelector(".load")
        .addEventListener("click", () => this.handleLoadTemplate(name));
      item
        .querySelector(".delete")
        .addEventListener("click", () => this.handleDeleteTemplate(name));

      list.appendChild(item);
    });
  },

  openTemplateManager() {
    const mgr = document.getElementById("template-manager");
    if (mgr) {
      this.refreshTemplateList();
      this.resetWindowPosition("template-manager");
    }
  },

  closeTemplateManager() {
    const mgr = document.getElementById("template-manager");
    if (mgr) mgr.style.display = "none";
  },

  initTemplateManager() {
    const openBtn = document.getElementById("open-templates-btn");
    const closeBtn = document.getElementById("close-template-manager");
    const saveBtn = document.getElementById("save-new-template-btn");
    const mgr = document.getElementById("template-manager");
    const dragHandle = document.getElementById("template-manager-drag-handle");

    if (openBtn)
      openBtn.addEventListener("click", () => this.openTemplateManager());
    if (closeBtn)
      closeBtn.addEventListener("click", () => this.closeTemplateManager());
    if (saveBtn)
      saveBtn.addEventListener("click", () => this.handleSaveTemplate());

    if (mgr && dragHandle) {
      let isDragging = false;
      let offsetX = 0,
        offsetY = 0;

      dragHandle.addEventListener("mousedown", (e) => {
        if (e.target.closest("button") || e.target.closest("input")) return;
        isDragging = true;
        const rect = mgr.getBoundingClientRect();
        offsetX = e.clientX - rect.left;
        offsetY = e.clientY - rect.top;
        mgr.style.transform = "none";
        mgr.style.left = rect.left + "px";
        mgr.style.top = rect.top + "px";
        const onMouseMove = (e) => {
          let newLeft = e.clientX - offsetX;
          let newTop = e.clientY - offsetY;
          const rect = mgr.getBoundingClientRect();

          newLeft = Math.max(
            0,
            Math.min(newLeft, window.innerWidth - rect.width),
          );
          newTop = Math.max(
            0,
            Math.min(newTop, window.innerHeight - rect.height),
          );

          mgr.style.left = newLeft + "px";
          mgr.style.top = newTop + "px";
        };

        const onMouseUp = () => {
          isDragging = false;
          window.removeEventListener("mousemove", onMouseMove);
          window.removeEventListener("mouseup", onMouseUp);
        };

        window.addEventListener("mousemove", onMouseMove);
        window.addEventListener("mouseup", onMouseUp);
      });
    }
  },
};

window.WidgetLoader = WidgetLoader;
window.enterEditMode = () => WidgetLoader.enterEditMode();
window.exitEditMode = () => WidgetLoader.exitEditMode();

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => WidgetLoader.init());
} else {
  WidgetLoader.init();
}
