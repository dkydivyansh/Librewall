// === CLOCK WIDGET LOGIC ===

function updateClock() {
  const dayNames = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const now = new Date();
  let hours = now.getHours();
  let minutes = now.getMinutes();
  let seconds = now.getSeconds();
  const day = dayNames[now.getDay()];
  const ampm = hours >= 12 ? 'PM' : 'AM';
  
  hours = hours % 12;
  hours = hours ? hours : 12;
  hours = hours < 10 ? '0' + hours : hours;
  minutes = minutes < 10 ? '0' + minutes : minutes;
  seconds = seconds < 10 ? '0' + seconds : seconds;

  const timeString = `${hours}:${minutes}:${seconds} ${ampm}`;
  
  try {
    document.getElementById('clock-time').textContent = timeString;
    document.getElementById('clock-day').textContent = day;
  } catch (e) {}
}

// === NETWORK WIDGET LOGIC ===

let wsPort = null;
let networkWidgetEnabled = false;

// --- Helper Functions ---
function formatBits(bits, perSecond = false) {
    if (!bits || bits === 0) return '0 ' + (perSecond ? 'bps' : 'b');
    const k = 1000;
    const sizes = perSecond ? ['bps', 'Kbps', 'Mbps', 'Gbps', 'Tbps'] : ['b', 'Kb', 'Mb', 'Gb', 'Tb'];
    const i = Math.floor(Math.log(bits) / Math.log(k));
    return `${parseFloat((bits / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}
function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

// --- Main UI Update Function ---
function updateNetworkUI(data) {
    try {
        // 1. Traffic Data
        document.getElementById('upload-speed').textContent = formatBits(data.upload_bps, true);
        document.getElementById('download-speed').textContent = formatBits(data.download_bps, true);
        document.getElementById('total-sent').textContent = formatBytes(data.total_sent);
        document.getElementById('total-recv').textContent = formatBytes(data.total_recv);

        // 2. Listening Ports
        document.getElementById('listening-count').textContent = `(${data.listening_count})`; 
        const listeningList = document.getElementById('listening-list');
        let listeningHtml = '';
        if (data.listening_ports.length === 0) {
            listeningHtml = 'No listening ports found.';
        } else {
            listeningHtml += 'Port/Protocol'.padEnd(15) + 'Type'.padEnd(15) + 'Process\n';
            data.listening_ports.forEach(item => {
                let port = (item.port + ' (' + item.protocol + ')').padEnd(15);
                listeningHtml += `${port}${item.type.padEnd(15)}${item.process}\n`;
            });
        }
        listeningList.textContent = listeningHtml;

        // 3. Active Connections
        document.getElementById('active-count').textContent = `(${data.active_count})`; 
        const activeList = document.getElementById('active-list');
        let activeHtml = '';
        if (data.active_connections.length === 0) {
            activeHtml = 'No established connections found.';
        } else {
            activeHtml += 'IP Address'.padEnd(22) + 'Protocol'.padEnd(10) + 'Type'.padEnd(15) + 'Process\n';
            data.active_connections.forEach(item => {
                let ip = (item.ip + ':' + item.port).padEnd(22);
                activeHtml += `${ip}${item.protocol.padEnd(10)}${item.type.padEnd(15)}${item.process}\n`;
            });
        }
        activeList.textContent = activeHtml;

        // 4. Live Traffic Log (Newest at bottom)
        const trafficLog = document.getElementById('traffic-log-list');
        let trafficHtml = '';
        if (data.live_traffic_log.length === 0) {
            trafficHtml = '<div class="traffic-entry">Monitoring for new connections...</div>';
        } else {
            data.live_traffic_log.forEach(item => {
                trafficHtml += `<div class="traffic-entry">` +
                    `<span class="timestamp">${item.timestamp.padEnd(15)}</span>` +
                    `<span class="type ${item.type}">${item.type.padEnd(10)}</span>` +
                    `<span class="ip">${item.ip_port.padEnd(26)}</span>` +
                    `<span class="protocol">${item.protocol.padEnd(10)}</span>` +
                    `<span class="process">${item.process}</span>` +
                    `</div>`;
            });
        }
        trafficLog.innerHTML = trafficHtml;
        trafficLog.scrollTop = trafficLog.scrollHeight;

    } catch (e) {
        console.error("Failed to update Network UI:", e);
    }
}

// --- WebSocket Connection Logic ---
function connectWebSocket(port) {
    const wsStatus = document.getElementById('ws-status');
    if (!wsStatus) return; 

    wsStatus.textContent = 'Connecting...';
    wsStatus.className = '';
    console.log(`Attempting to connect to WebSocket at ws://localhost:${port}`);
    
    const socket = new WebSocket(`ws://localhost:${port}`);

    socket.onopen = () => {
        console.log('Network Widget: WebSocket connection established.');
        wsStatus.textContent = 'Connected';
        wsStatus.className = 'connected';
    };
    socket.onmessage = (event) => {
        updateNetworkUI(JSON.parse(event.data));
    };
    socket.onclose = () => {
        console.log('Network Widget: WebSocket closed. Retrying in 3s...');
        wsStatus.textContent = 'Disconnected';
        wsStatus.className = 'error';
        setTimeout(() => connectWebSocket(port), 3000);
    };
    socket.onerror = (error) => {
        console.error('Network Widget: WebSocket error:', error);
        wsStatus.textContent = 'Error';
        wsStatus.className = 'error';
    };
}

// --- Initialization ---
async function initNetworkWidget() {
    try {
        const configResponse = await fetch('/config');
        const config = await configResponse.json();
        
        // --- MODIFIED: Check for either the new OR old flag ---
        networkWidgetEnabled = config.Enable_Global_Widget === true || config.Enable_Network_Widget === true;

        const networkWidgets = [
            'traffic-data', 'listening-ports', 
            'live-traffic-log', 'active-connections'
        ];
        
        const clockWidget = document.getElementById('live-clock');

        if (!networkWidgetEnabled) {
            // --- MODIFIED: Updated log message ---
            console.log("Network/Global Widgets are disabled by config.json. Hiding UI.");
            networkWidgets.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.style.display = 'none';
            });
            if (clockWidget) clockWidget.style.display = 'none'; // Also hide clock
            return;
        }

        // --- This part now only runs if widgets are enabled ---
        const appConfigResponse = await fetch('/app_config.json');
        const appConfig = await appConfigResponse.json();
        wsPort = appConfig.ws_port;

        if (wsPort) {
            connectWebSocket(wsPort);
        } else {
            console.error("Could not get 'ws_port' from app_config.json.");
            const wsStatus = document.getElementById('ws-status');
            if(wsStatus) {
                wsStatus.textContent = 'No Port';
                wsStatus.className = 'error';
            }
        }
    } catch (e) {
        console.error("Failed to initialize Network Widget:", e);
    }
}


// === DRAGGABLE & RESIZABLE WIDGET LOGIC ===

let isDraggable = false;
let activeContainer = null;
let offsetX = 0, offsetY = 0;
let isResizing = false;
let originalWidth = 0, originalHeight = 0;
let originalMouseX = 0, originalMouseY = 0;

async function savePositions() {
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
        const response = await fetch('/save_widget_positions', { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(positions)
        });
        if (response.ok) {
            console.log("Draggable widget positions and sizes saved to server (widget.json).");
        } else {
            console.error("Failed to save positions to server.");
        }
    } catch (e) {
        console.error("Error saving positions:", e);
    }
}

// --- NEW: Function to apply default positions ---
function applyDefaultPositions() {
    console.log("Applying default widget positions.");
    const defaultPositions = {
        "live-clock": { "top": "72.5938px", "left": "1709px", "right": "auto", "width": "778px", "height": "181px" },
        "traffic-data": { "top": "1072.59px", "left": "31px", "right": "auto", "width": "432px", "height": "251.594px" },
        "listening-ports": { "top": "35.7969px", "left": "36px", "right": "auto", "width": "425px", "height": "994.594px" },
        "live-traffic-log": { "top": "891.188px", "left": "1808.8px", "right": "auto", "width": "683.188px", "height": "476.594px" },
        "active-connections": { "top": "299.391px", "left": "1812.81px", "right": "auto", "width": "675.188px", "height": "572px" }
    };
    
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
}

// --- MODIFIED: restorePositions now uses defaults as a fallback ---
async function restorePositions() {
    try {
        const response = await fetch('/widget.json');
        if (!response.ok) {
            console.log("widget.json not found, using default CSS positions.");
            applyDefaultPositions(); // <-- Use defaults
            return; 
        }
        
        const positions = await response.json();
        
        if (positions && Object.keys(positions).length > 0) {
            Object.keys(positions).forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    const pos = positions[id];
                    if(pos.top) el.style.top = pos.top;
                    // --- THIS IS THE FIX ---
                    if(pos.left) el.style.left = pos.left; 
                    // --- END FIX ---
                    if(pos.right) el.style.right = pos.right;
                    
                    if (pos.right && pos.left === 'auto') {
                        el.style.left = 'auto';
                    } else {
                        el.style.right = 'auto';
                    }
                    
                    if (pos.width) el.style.width = pos.width;
                    if (pos.height) el.style.height = pos.height;
                }
            });
            console.log("Draggable widget positions and sizes restored from server (widget.json).");
        } else {
            // File was found but was empty, use defaults
            console.log("widget.json was empty, using default positions.");
            applyDefaultPositions();
        }
    } catch (e) {
        // File was corrupt or another error, use defaults
        console.error("Failed to restore widget positions:", e);
        applyDefaultPositions();
    }
}

// --- (Drag/Resize functions are unchanged) ---

// --- DRAG (Move) Functions ---
function onContainerMouseDown(e) {
    if (!isDraggable || e.target.classList.contains('resize-handle')) return;
    e.preventDefault(); 
    activeContainer = e.target.closest('.widget-container');
    const rect = activeContainer.getBoundingClientRect();
    offsetX = e.clientX - rect.left;
    offsetY = e.clientY - rect.top;
    window.addEventListener('mousemove', onDragMove);
    window.addEventListener('mouseup', onDragEnd);
}
function onDragMove(e) {
    if (!activeContainer) return;
    let newX = e.clientX - offsetX;
    let newY = e.clientY - offsetY;
    activeContainer.style.left = `${newX}px`;
    activeContainer.style.top = `${newY}px`;
    activeContainer.style.right = 'auto'; 
}
function onDragEnd() {
    activeContainer = null;
    window.removeEventListener('mousemove', onDragMove);
    window.removeEventListener('mouseup', onDragEnd);
}

// --- RESIZE Functions ---
function onResizeMouseDown(e) {
    if (!isDraggable) return;
    e.preventDefault();
    e.stopPropagation();
    isResizing = true;
    activeContainer = e.target.closest('.widget-container');
    const rect = activeContainer.getBoundingClientRect();
    originalWidth = rect.width;
    originalHeight = rect.height;
    originalMouseX = e.clientX;
    originalMouseY = e.clientY;
    window.addEventListener('mousemove', onResizeDrag);
    window.addEventListener('mouseup', onResizeEnd);
}
function onResizeDrag(e) {
    if (!isResizing || !activeContainer) return;
    const deltaX = e.clientX - originalMouseX;
    const deltaY = e.clientY - originalMouseY;
    activeContainer.style.width = `${originalWidth + deltaX}px`;
    activeContainer.style.height = `${originalHeight + deltaY}px`;
}
function onResizeEnd() {
    isResizing = false;
    activeContainer = null;
    window.removeEventListener('mousemove', onResizeDrag);
    window.removeEventListener('mouseup', onResizeEnd);
}

// --- Event Handlers ---
function onContainerDoubleClick(e) {
    const container = e.target.closest('.widget-container');
    if (container && !isDraggable) {
        isDraggable = true;
        document.body.classList.add('is-dragging');
        console.log("Edit Mode ENABLED. Click background to save.");
    }
}
function onBackgroundClick() {
    if (isDraggable) {
        isDraggable = false;
        document.body.classList.remove('is-dragging');
        savePositions();
        console.log("Edit Mode DISABLED. Positions saved.");
    }
}

async function initDraggableSystem() {
    await restorePositions(); 
    
    document.querySelectorAll('.widget-container').forEach(container => {
        container.addEventListener('dblclick', onContainerDoubleClick);
        container.addEventListener('mousedown', onContainerMouseDown);
    });
    document.querySelectorAll('.resize-handle').forEach(handle => {
        handle.addEventListener('mousedown', onResizeMouseDown);
    });
    const bgCatcher = document.getElementById('background-click-catcher');
    if (bgCatcher) {
        bgCatcher.addEventListener('click', onBackgroundClick);
    }
}

// === MAIN INITIALIZATION ===
updateClock();
setInterval(updateClock, 1000);

initNetworkWidget();
initDraggableSystem();