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

```javascript
(function () {
    const WIDGET_ID = 'my-widget';

    window.getWidgetContent_myWidget = function () {
        return {
            id: WIDGET_ID,
            html: `
                <h2>My Widget</h2>
                <div id="my-content">Hello World</div>
            `,
            settings: {
                minWidth: '200px',
                minHeight: '150px'
            },
            init: function () {
                // Called when widget loads
                console.log('Widget initialized');
            },
            destroy: function () {
                // Called when widget is removed
                // Clean up intervals, listeners, etc.
            }
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

Add your widget to `widgets/index.json`:

```json
{
    "id": "my-widget",
    "name": "My Widget",
    "author": "Your Name",
    "authorUrl": "https://yoursite.com",
    "folder": "my-widget",
    "version": "1.0.0"
}
```

## Function Naming

The function name must follow camelCase format:
- Widget ID: `my-widget` → Function: `getWidgetContent_myWidget`
- Widget ID: `weather` → Function: `getWidgetContent_weather`
- Widget ID: `live-clock` → Function: `getWidgetContent_liveClock`

## Settings Reference

| Setting | Type | Description |
|---------|------|-------------|
| `minWidth` | string | Minimum width (e.g., `'300px'`) |
| `minHeight` | string | Minimum height (e.g., `'200px'`) |

### Example

```javascript
settings: {
    minWidth: '320px',
    minHeight: '220px'
}
```

## Lifecycle

1. **Load**: Widget JS/CSS files are dynamically injected
2. **Render**: `html` content is inserted into DOM
3. **Init**: `init()` is called after render
4. **Destroy**: `destroy()` is called when widget is hidden/removed

## Best Practices

### Use Unique IDs
Prefix all element IDs with your widget name:
```javascript
html: `<div id="mywidget-content">...</div>`
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
        const response = await fetch('https://api.example.com/data');
        const data = await response.json();
        updateUI(data);
    } catch (error) {
        console.error('Fetch failed:', error);
        showError();
    }
}
```

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
        id: 'my-widget',
        html: `...`,
        settings: {
            minWidth: '300px',
            minHeight: '200px'
        },
        editableSettings: [
            { key: 'title', label: 'Title', type: 'string', value: 'Default Title' },
            { key: 'refreshRate', label: 'Refresh Rate (sec)', type: 'integer', value: 30 },
            { key: 'opacity', label: 'Opacity', type: 'slider', min: 0, max: 100, value: 80 },
            { key: 'accentColor', label: 'Color', type: 'color', value: '#4a90e2' }
        ],
        updateStyle: function (settings) {
            // Called when user applies new settings
            if (settings.title) {
                document.getElementById('my-title').innerText = settings.title;
            }
            // Re-fetch data with new settings, update UI, etc.
        },
        init: function () {},
        destroy: function () {}
    };
};
```

### Setting Types

| Type | Description | Extra Properties |
|------|-------------|------------------|
| `string` | Text input | - |
| `integer` | Number input | - |
| `slider` | Range slider | `min`, `max` (default: 0-100) |
| `color` | Color picker | - |
| `select` | Dropdown select | `options` (array of strings or `{value, label}` objects) |

### Select Example

```javascript
editableSettings: [
    { 
        key: 'units', 
        label: 'Temperature Units', 
        type: 'select', 
        value: 'celsius',
        options: [
            { value: 'celsius', label: 'Celsius (°C)' },
            { value: 'fahrenheit', label: 'Fahrenheit (°F)' }
        ]
    }
]
```

### Loading Saved Settings

Use `WidgetLoader.getStyles(widgetId)` to retrieve saved values:

```javascript
window.getWidgetContent_myWidget = function () {
    const saved = typeof WidgetLoader !== 'undefined' ? WidgetLoader.getStyles('my-widget') : {};
    const title = saved.title || 'Default';
    
    return {
        // ... use title in your HTML/settings
    };
};
```

### Context Menu

Users can left-click any widget to open a context menu with:
- **Edit Settings** - Opens the settings editor
- **Hide Widget** - Hides the widget
