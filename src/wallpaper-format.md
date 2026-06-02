# Cyberwall Wallpaper Format Documentation

This document provides a comprehensive overview of the different wallpaper types, how the internal engine loads wallpapers, supported formats, and all available settings in `config.json`.

## 1. Wallpaper Engine Modes

The wallpaper system utilizes a priority-based engine structure to determine how to render the active theme. The mode is selected based on the configuration inside `config.json` (specifically the `videorender` and `htmlrender` booleans).

### Mode 1: Native Video Render (`videorender: true`)
- **Priority:** Highest. If `videorender` is set to `true`, the engine uses the Native MPV player to present a video loop.
- **Best Use Case:** 4K/8K video loops without 3D elements.
- **Behavior:** This mode entirely ignores 3D settings and WebGL scenes.

### Mode 2: HTML Render Mode (`htmlrender: true`)
- **Priority:** Medium. Used if `videorender: false` and `htmlrender: true`.
- **Best Use Case:** Fully custom CodePen-like creations, 2D Canvas games, or highly detailed HTML/CSS/JS web designs.
- **Behavior:** The engine skips the built-in 3D engine script (`index.html`) and directly serves the `htmlWidgetFile` (e.g., your custom HTML file) as the root page. 

### Mode 3: 3D WebGL Engine (Three.js)
- **Priority:** Default. Used if both `videorender` and `htmlrender` are `false`.
- **Best Use Case:** Interactive 3D models with lighting, bloom, shadows, and interactive mouse responses.
- **Behavior:** Runs `index.html` containing the custom Three.js renderer. Further behavior depends on `enable3DModel`:
  - **Full 3D Mode (`enable3DModel: true`):** Loads a GLTF/GLB model, renders lighting, shadows, and post-processing, overlaying custom HTML widgets on top.
  - **2D/Media Mode (`enable3DModel: false`):** Runs the engine but hides the 3D canvas, rendering only the background media (image/video loop) and injecting custom HTML/JS widgets.

## 2. Supported Formats

- **3D Models:** `.glb` (GLTF Binary is standard via GLTFLoader).
- **Background Media (WebGL mode):**
  - **Video:** `.mp4`, `.webm`, `.ogg`, `.mov`
  - **Images:** `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`
- **Environment HDRs:** `.hdr` format (Equirectangular) for physical lighting.
- **Widgets:** `.html`, `.css`, `ES6 Module .js`.

## 3. How Wallpapers Load

1. **Local HTTP Server (`main.py`):** The python backend spins up a local HTTP/WebSocket server. It reads `app_config.json` to find the `active_theme`.
2. **Routing:** Incoming requests for the root `/` URL serve either the internal WebGL `index.html` engine or the theme's custom HTML file (if `htmlrender` is on).
3. **Asset Fetching (`index.html`):**
   - The frontend JavaScript does an `await fetch('/config')` to fetch the current theme's `config.json`.
   - The script sets up the `THREE.WebGLRenderer`, setting pixel ratios and quality parameters based on `qualityPreset`.
   - **Backgrounds:** A `<video>` or `<img>` element (`#background-media`) is injected underneath the 3D canvas if a `backgroundMedia` path is defined.
   - **Environment:** If `enableEnvironmentHDR` is true, an `.hdr` texture is retrieved and set via `PMREMGenerator`.
   - **3D Model:** The `GLTFLoader` asynchronously requests `/model` (which the engine routes securely to your specific `modelFile`), placing it in the scene, modifying materials (metalness/roughness) based on config flags, and starting animation mixers.
   - **Widgets:** If global widgets are true, system widgets are injected. Otherwise, local widgets (from `htmlWidgetFile`, `cssFile`, `logicFile`) are injected securely into the DOM.

## 4. Complete Reference: `config.json`

Below is a detailed list of available settings in `config.json`.

### Metadata
*   `metadata.themeName` (String): The name of your wallpaper.
*   `metadata.author` (String): Creator name.
*   `metadata.authorUrl` (String): Creator link.
*   `metadata.description` (String): Description.
*   `metadata.thumbnailImage` (String): File name of the preview image inside the theme folder.

### Engine Mode Toggles
*   `videorender` (Boolean): Force native MPV video rendering.
*   `htmlrender` (Boolean): Force native HTML-only rendering.
*   `enable3DModel` (Boolean): Loads a 3D model into the WebGL scene.

### Media & Video Settings
*   `media` (String): File name of the video play for Native MPV.
*   `fpsLimit` (Number): Throttles framerate for Video and 3D modes. `0` = Unlimited.
*   `muteAudio` (Boolean): Mutes video audio loops.
*   `volume` (Number): 0-100 audio magnitude.

### Quality & Engine Settings (3D Mode)
*   `qualityPreset` (String): Options are `'low'` (0.6x res, no shadows/bloom), `'medium'` (0.85x res, bloom on), `'high'` (1.0x res, full FX), `'ultra'` (Uses device native DPI).
*   `toneMapping` (String): Options: `'Filmic'`, `'Reinhard'`, `'AgX'`, `'None'`, `'Linear'`. Usually use `Filmic`.
*   `toneMappingExposure` (Number): Default `1.0`. Exposure multiplier.
*   `enableShadows` (Boolean): Enables PCF soft shadows and casts on lights/models.
*   `enableEnvironmentHDR` (Boolean): Determines if image-based lighting from an HDR is used.

### Model Settings
*   `modelFile` (String): Relative path to `.glb` file.
*   `modelScale` (Number): Multiplier to size the model.
*   `modelFrontRotation` (Object: `{x, y, z}` in degrees): Base rotation offsets for the model.
*   `forceMaterialOverride` (Boolean): If true, overrides all materials strictly.
*   `overrideMetalness` (Number 0.0-1.0): Forced metallic factor.
*   `overrideRoughness` (Number 0.0-1.0): Forced roughness factor.

### Post-Processing
*   `enableBloom` (Boolean): Turns on UnrealBloomPass for glowing emissive textures.
*   `bloomStrength` (Number): Multiplier.
*   `bloomRadius` (Number): Spread area.
*   `bloomThreshold` (Number): Brightness cutoff where bloom takes effect.

### Background Renderers
*   `backgroundMedia` (String): Path to a looping video or image rendered seamlessly underneath the 3D scene.
*   `backgroundCSS` (String): A raw CSS property for `#wallpaper-background`'s background attribute (e.g. `linear-gradient(...)`).

### Interactivity
*   `enableIdleRotation` (Boolean): When mouse is idle for 10 seconds, revolves model slowly.
*   `enableMouseAttraction` (Boolean): Parallax effect making the model tilt subtly to track the mouse cursor coordinates.

### Lighting Setup
*   `lights` (Array of objects): Configure custom lighting sources.
    **Common Properties:**
    *   `type`: `'AmbientLight'`, `'DirectionalLight'`, `'SpotLight'`, `'PointLight'`
    *   `color`: Hex Code `"#FFFFFF"`
    *   `intensity`: Strength multiplier.
    *   `position`: `{x, y, z}` coords (For Spot, Point, Directional)
    *   `decay` / `distance`: Falloff definitions. (For Spot, Point)
    *   `angle` / `penumbra`: Cone constraints. (For SpotLight)

### Advanced Shadow Maps
*   `shadowBias` (Number): Fixes shadow acne (commonly `-0.0001`).
*   `shadowMapSizeWidth` / `shadowMapSizeHeight` (Number): Shadow resolution (e.g., 1024 / 2048).

### UI / Widget Injection
*   `Enable_Global_Widget` (Boolean): If true, ignores local widgets and applies system-wide monitor widgets (if configured locally on the device).
*   `htmlWidgetFile` (String): Local `.html` file injected onto `#external-widget-root` HUD layer.
*   `cssFile` (String): Local `.css` file injected into the head.
*   `logicFile` (String): Local `.js` (module type scripting) injected into body.
