# Widget Development Guide

This guide explains how to create custom widgets for Cyberwall.

## Widget Structure

Each widget lives in its own folder under `widgets/`:

```
widgets/
├── index.json           # Widget registry
└── your-widget/
    ├── main.js          # Widget logic
    └── style.css        # Widget styles
```

## Quick Start

### 1. Create Widget Folder

```
widgets/my-widget/
├── main.js
└── style.css
```

### 2. Create main.js

You must include a metadata comment block at the top of `main.js`. This is parsed by the launcher during import to display information to the user.

```javascript
/*
@name: My Widget
@author: Your Name
@description: A cool widget that does things.
@min_version: 1
*/

export default class MyWidget {
  constructor(id) {
    this.id = id;
    this.html = `
      <h2>My Widget</h2>
      <div id="${this.id}-content">Hello World</div>
    `;
    this.settings = {
      minWidth: "200px",
      minHeight: "150px"
    };
  }

  init() {}

  destroy() {}
}
```

### 3. Create style.css

```css
#my-widget {
  /* Container styles handled by global.css */
}

#my-widget h2 {
  color: #fff;
  margin: 0 0 10px 0;
}

#my-content {
  color: #ccc;
}
```

### 4. Register in index.json

Add your widget to `widgets/index.json`. Note that the registry is an object containing a `widgets` array:

```json
{
  "widgets": [
    {
      "id": "my-widget",
      "name": "My Widget",
      "author": "Your Name",
      "authorUrl": "https://yoursite.com",
      "folder": "my-widget",
      "ver": 1
    }
  ]
}
```

### 5. Backend Module Subscriptions (Optional)

If your widget requires heavy background processing from the Python backend (like network packet sniffing, active connections, or media telemetry), you can explicitly "subscribe" to those modules within your widget class.

The `global.js` WidgetLoader will automatically wake up the corresponding Python threads when your widget is toggled **on**, and safely put them back to sleep to save CPU when toggled **off**.

Simply add a `this.modules` array to your widget's constructor in `main.js`:

```javascript
export default class MyWidget {
    constructor(id) {
        this.id = id;
        this.html = `...`;
        this.settings = {};
        
        // Define backend dependencies
        this.modules = ["live_traffic_log", "active_connections"];
    }
}
```

**Available Core Modules:**
- `active_connections`: Scans the system for all active ESTABLISHED connections.
- `listening_count`: Scans the system for all open LISTEN ports.
- `live_traffic_log`: Logs all outbound/inbound traffic events continuously.
- `traffic_stats`: Calculates active upload/download bytes per second.
- `media`: Hooks into the Windows SMTC to provide playback status, duration, and thumbnail APIs.

---

## Settings Reference

| Setting       | Type    | Description                                                                   |
| ------------- | ------- | ----------------------------------------------------------------------------- |
| `minWidth`    | string  | Minimum width (e.g., `'300px'`)                                               |
| `minHeight`   | string  | Minimum height (e.g., `'200px'`)                                              |
| `width`       | string  | Current/initial width (applied to container)                                  |
| `height`      | string  | Current/initial height (applied to container)                                 |
| `top`         | string  | Vertical position (e.g., `'40px'`)                                            |
| `left`        | string  | Horizontal position (e.g., `'20px'`)                                          |
| `right`       | string  | Horizontal anchor (e.g., `'20px'`, sets `left` to `auto`)                     |
| `transparent` | boolean | If `true`, removes container background, backdrop-filter, shadow, and border. |
| `fixedSize`   | boolean | If `true`, container fits content exactly and resizing is disabled.           |

### Example

```javascript
this.settings = {
  minWidth: "320px",
  minHeight: "220px"
};
```

## Lifecycle

1. **Load (Lazy)**: Widget JS/CSS files are purely dynamically injected via ESM **only** if the widget is enabled. Disabled widgets are completely isolated and never execute code, preserving RAM and background network connections.
2. **Render**: Class is instantiated. The \`html\` string is injected into a \`.widget-container\`. Styles like \`transparent\` or \`fixedSize\` are mapped. Core drag listeners and the \`.resize-handle\` are automatically attached to the container by \`global.js\`.
3. **Init**: \`init()\` is called immediately after render. This is where you should find your elements (\`document.getElementById\`) and bind widget-specific logic or fetches.
4. **Destroy (Purge)**: \`destroy()\` is called when a widget is toggled off in the Edit menu. **Important**: \`global.js\` physically deletes your widget container DOM node and purges your \`.css\` link tag. Your \`destroy()\` method *must* sever any remaining ties (intervals, tweens, window event listeners, or external APIs) so the JavaScript Garbage Collector can fully wipe the widget from memory.

## Best Practices

### Use Unique IDs

Prefix all element IDs with your widget name:

```javascript
html: `<div id="mywidget-content">...</div>`;
```

### Clean Up Resources (Critical)

Because widgets are dynamically loaded and unloaded, failure to clean up resources guarantees CPU leaks, RAM spikes, and Ghost instances (where background processing continues after the widget vanishes). 

Always clean up in `destroy()`:

```javascript
let interval = null;
const handleMouseMove = (e) => { ... };

init: function() {
    interval = setInterval(update, 1000);
    // Be very careful with document/window listeners! They persist forever if not removed.
    document.addEventListener("mousemove", handleMouseMove); 
},
destroy: function() {
    // 1. Clear Timers
    if (interval) clearInterval(interval);
    
    // 2. Clear Global Listeners
    document.removeEventListener("mousemove", handleMouseMove);
    
    // 3. Kill heavy external instances (GSAP, YouTube Players, etc.)
    if (this.myTween) this.myTween.kill();
    if (this.player) this.player.destroy();
}
```

### External APIs

For API calls, handle errors gracefully:

```javascript
function fetchData() {
  // ...
}
```

## External Libraries

If your widget depends on external libraries (like GSAP, Three.js, etc.) that you import via ESM, you must ensure they are properly cached on the global `window` object. This prevents crashes when users toggle your widget on and off.

Because the `WidgetLoader` dynamically imports and unloads widgets, an `import()` statement may return a cached module, but the `window` reference might need checking.

### Best Practice: Caching Libraries

```javascript
async init() {
    // 1. Check/Load Core Library
    if (typeof window.gsap === "undefined") {
        const gsapModule = await import("./gsap.js");
        window.gsap = gsapModule.gsap || gsapModule.default || gsapModule;
    }
    this.gsap = window.gsap;

    // 2. Check/Load Plugins independently
    if (typeof window.Draggable === "undefined") {
        const DraggableModule = await import("./Draggable.js");
        window.Draggable = DraggableModule.Draggable || DraggableModule.default;
        this.gsap.registerPlugin(window.Draggable);
    }
    this.Draggable = window.Draggable;
}
```

This pattern ensures that `this.gsap` and `this.Draggable` are always defined, even if the widget is re-initialized multiple times without a full page refresh.

## Bypass Proxy

Cyberwall provides a local bypass proxy to help widgets fetch data from external APIs that might otherwise block requests due to CORS (Cross-Origin Resource Sharing), strict SSL/TLS requirements, or bot detection.

### Usage

Prepend `/proxy?url=` to your target URL. For best results, use `encodeURIComponent()` on the target URL.

```javascript
async function fetchData() {
  const targetUrl = "https://api.example.com/data";
  const proxiedUrl = `/proxy?url=${encodeURIComponent(targetUrl)}`;

  try {
    const response = await fetch(proxiedUrl);

    if (!response.ok) {
      // Handle errors (Proxy forwards actual status codes like 404, 503, etc.)
      const errorText = await response.text();
      console.warn(`Fetch error ${response.status}: ${errorText}`);
      return;
    }

    const data = await response.json();
    updateUI(data);
  } catch (error) {
    // Handle network/DNS/SSL errors (Proxy returns 502 for connection resets)
    const errorText = (await error.text) ? await error.text() : error.message;
    console.error("Connectivity issue:", errorText);
  }
}
```

### Features

- **CORS Bypass**: Automatically adds `Access-Control-Allow-Origin: *` to the response.
- **Header Spoofing**: Automatically injects a real browser `User-Agent` and spoofs `Referer`/`Origin` headers to bypass bot detection.
- **Custom Spoofing**: You can provide your own spoofing headers if the target has specific requirements:
  - `X-Proxy-Referer`: Overrides the Referer header sent to the target.
  - `X-Proxy-Origin`: Overrides the Origin header sent to the target.
- **Transparent Errors**: Forwards actual HTTP status codes from the target server. For network-level failures (like a connection reset or SSL error), it returns `502 Bad Gateway`.

---

## Default Visibility

New widgets are **hidden by default**. Users enable them via the Edit Widgets menu (double-click any widget to open).

## Examples

See existing widgets for reference:

- `widgets/clock/` - Simple timer widget
- `widgets/weather/` - API integration + animations + editable settings

---

## Editable Settings System

Widgets can expose editable settings that users can modify through the settings editor.

### Widget Implementation

Add `editableSettings` array and `updateStyle` function to your widget:

```javascript
export default class MyWidget {
  constructor(id) {
    this.id = id;
    this.html = `...`;
    this.settings = {
      minWidth: "300px",
      minHeight: "200px"
    };
    this.editableSettings = [
      { key: "title", label: "Title", type: "string", value: "Default Title" },
      { key: "refreshRate", label: "Refresh Rate (sec)", type: "integer", value: 30 },
      { key: "opacity", label: "Opacity", type: "slider", min: 0, max: 100, value: 80 },
      { key: "accentColor", label: "Color", type: "color", value: "#4a90e2" }
    ];
  }

  updateStyle(settings) {
    if (settings.title) {
      document.getElementById("my-title").innerText = settings.title;
    }
  }

  init() {}

  destroy() {}
}
```

### Setting Types

| Type      | Description           | Extra Properties                                                   |
| --------- | --------------------- | ------------------------------------------------------------------ |
| `string`  | Text input            | -                                                                  |
| `integer` | Number input          | -                                                                  |
| `slider`  | Range slider (0-100%) | `min`, `max` (defaults to 0-100). The UI appends `%` to the label. |
| `color`   | Color picker          | -                                                                  |
| `boolean` | Checkbox toggle       | -                                                                  |
| `select`  | Dropdown select       | `options` (array of strings or `{value, label}` objects)           |

### Select Example

```javascript
editableSettings: [
  {
    key: "units",
    label: "Temperature Units",
    type: "select",
    value: "celsius",
    options: [
      { value: "celsius", label: "Celsius (°C)" },
      { value: "fahrenheit", label: "Fahrenheit (°F)" },
    ],
  },
];
```

### Loading Saved Settings

Use `WidgetLoader.getStyles(widgetId)` to retrieve saved values:

```javascript
export default class MyWidget {
  constructor(id) {
    this.id = id;
    const saved = typeof WidgetLoader !== "undefined" ? WidgetLoader.getStyles(id) : {};
    const title = saved.title || "Default";

    // ... use title in your HTML/settings
  }
}
```

### Context Menu & Edit Mode

When the user enters Edit Mode (`WidgetLoader.isDraggable = true`), clicks are intercepted by `global.js` for layout management.

- **Opening Menu**: Left-clicking empty space on any widget opens the Context Menu ("Edit Settings" / "Hide Widget").
- **Exemptions**: Clicking elements that naturally require interaction (`button`, `input`, `a`, `canvas`, or the `.resize-handle`) will **not** trigger the Context Menu. Design your UI so that interactable buttons don't accidentally block users from configuring the widget!

---

## Media API Integration

Cyberwall provides a built-in media integration API that hooks directly into the host OS's native media transport controls (Windows SMTC). This allows widgets to act as fully-featured media players with live metadata, playback controls, and cover art.

### 1. Live Metadata (`librewall-data` Event)

The engine broadcasts live system telemetry over a local WebSocket. Every second, widgets receive a `librewall-data` CustomEvent on the `window` object containing a `media` dictionary.

```javascript
window.addEventListener('librewall-data', (e) => {
    const data = e.detail;
    if (!data.media) return;
    
    console.log(data.media);
    /* Example Output:
    {
        "title": "Song Name",
        "artist": "Artist Name",
        "album": "Album Name",
        "state": "Playing", // "Playing", "Paused", "Stopped"
        "position": 14.5, // Current time in seconds
        "end_time": 180.0, // Total duration in seconds
        "has_thumbnail": true
    }
    */
});
```

### 2. Media Controls API

You can control the system media transport using HTTP GET requests to the `/media/control` endpoint.

```javascript
// Play or Pause
fetch('/media/control?action=play');
fetch('/media/control?action=pause');

// Skip Tracks
fetch('/media/control?action=next');
fetch('/media/control?action=prev');
```

*Note: Because these are HTTP requests to the local engine, they execute instantly. You can combine these with optimistic UI updates for maximum responsiveness.*

### 3. Live Cover Art (Thumbnail API)

If `has_thumbnail` is `true`, you can fetch the raw image blob directly from the `/media/thumbnail` endpoint. 

To prevent flickering when polling, use the song title and artist as a cache key and only reload the image `src` when the track changes!

```javascript
// Append a timestamp to bypass browser image caching
const newSrc = \`/media/thumbnail?t=\${Date.now()}\`;

const img = new Image();
img.onload = () => { document.getElementById('cover-art').src = newSrc; };
img.src = newSrc;
```
