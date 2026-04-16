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

(function () {
  const script = document.currentScript;
  const WIDGET_ID = script.dataset.widgetId;

  window["getWidgetContent_" + WIDGET_ID] = function () {
    return {
      id: WIDGET_ID,
      html: `
                <h2>My Widget</h2>
                <div id="${WIDGET_ID}-content">Hello World</div>
            `,
      settings: {
        minWidth: "200px",
        minHeight: "150px",
      },
      init: function () {
        console.log("Widget initialized:", WIDGET_ID);
      },
      destroy: function () {},
    };
  };
})();
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

## Function Naming

The launcher is flexible and will search for the content function in several formats based on your Widget ID (e.g., `my-widget`):

1. **camelCase**: `getWidgetContent_myWidget` (Recommended)
2. **Kebab-case**: `getWidgetContent_my-widget`
3. **Flat**: `getWidgetContent_mywidget` (No dashes)

Example ID mappings:

- `live-clock` → `getWidgetContent_liveClock`
- `weather` → `getWidgetContent_weather`

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
settings: {
    minWidth: '320px',
    minHeight: '220px'
}
```

## Lifecycle

1. **Load**: Widget JS/CSS files are dynamically injected.
2. **Render**: `html` content is inserted into a `.widget-container`. An automatic `.resize-handle` is added.
3. **Init**: `init()` is called after render.
4. **Destroy**: `destroy()` is called when widget is hidden/removed.

## Best Practices

### Use Unique IDs

Prefix all element IDs with your widget name:

```javascript
html: `<div id="mywidget-content">...</div>`;
```

### Clean Up Resources

Always clean up in `destroy()`:

```javascript
let interval = null;

init: function() {
    interval = setInterval(update, 1000);
},
destroy: function() {
    if (interval) {
        clearInterval(interval);
        interval = null;
    }
}
```

### External APIs

For API calls, handle errors gracefully:

```javascript
async function fetchData() {
  try {
    const response = await fetch("https://api.example.com/data");
    const data = await response.json();
    updateUI(data);
  } catch (error) {
    console.error("Fetch failed:", error);
    showError();
  }
}
```

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
window.getWidgetContent_myWidget = function () {
  return {
    id: "my-widget",
    html: `...`,
    settings: {
      minWidth: "300px",
      minHeight: "200px",
    },
    editableSettings: [
      { key: "title", label: "Title", type: "string", value: "Default Title" },
      {
        key: "refreshRate",
        label: "Refresh Rate (sec)",
        type: "integer",
        value: 30,
      },
      {
        key: "opacity",
        label: "Opacity",
        type: "slider",
        min: 0,
        max: 100,
        value: 80,
      },
      { key: "accentColor", label: "Color", type: "color", value: "#4a90e2" },
    ],
    updateStyle: function (settings) {
      // Called when user applies new settings
      if (settings.title) {
        document.getElementById("my-title").innerText = settings.title;
      }
      // Re-fetch data with new settings, update UI, etc.
    },
    init: function () {},
    destroy: function () {},
  };
};
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
window.getWidgetContent_myWidget = function () {
  const saved =
    typeof WidgetLoader !== "undefined"
      ? WidgetLoader.getStyles("my-widget")
      : {};
  const title = saved.title || "Default";

  return {
    // ... use title in your HTML/settings
  };
};
```

### Context Menu

Users can left-click any widget to open a context menu with:

- **Edit Settings** - Opens the settings editor
- **Hide Widget** - Hides the widget
