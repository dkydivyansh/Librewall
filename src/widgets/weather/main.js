(function () {
    const WIDGET_ID = 'weather';

    const CONFIG = {
        lat: 40.7128,

        lon: -74.0060,

        city: "New York",

        units: "celsius",

        showLocation: "show",
        showDate: "show"
    };

    let snowInterval = null;
    let refreshInterval = null;

    window.getWidgetContent_weather = function () {

        const savedStyles = typeof WidgetLoader !== 'undefined' ? WidgetLoader.getStyles(WIDGET_ID) : {};
        console.log('Weather widget loaded styles:', savedStyles);

        if (savedStyles.city) CONFIG.city = savedStyles.city;
        if (savedStyles.lat) CONFIG.lat = parseFloat(savedStyles.lat);
        if (savedStyles.lon) CONFIG.lon = parseFloat(savedStyles.lon);
        if (savedStyles.units) CONFIG.units = savedStyles.units;
        if (savedStyles.showLocation) CONFIG.showLocation = savedStyles.showLocation;
        if (savedStyles.showDate) CONFIG.showDate = savedStyles.showDate;

        return {
            id: WIDGET_ID,
            html: `
                <div class="weather-content">
                    <div id="weather-snow-container"></div>

                    <div class="weather-top">
                        <div class="weather-location" style="display: ${CONFIG.showLocation === 'hide' ? 'none' : 'flex'}">
                            <svg width="14" height="14" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
                            </svg>
                            <span id="weather-city">Loading...</span>
                        </div>
                        <div class="weather-date" id="weather-date" style="display: ${CONFIG.showDate === 'hide' ? 'none' : 'block'}"></div>
                    </div>

                    <div class="weather-main">
                        <h1 class="weather-temp" id="weather-temp">--</h1>
                        <p class="weather-condition" id="weather-condition">Fetching...</p>
                    </div>

                    <div class="weather-details">
                        <div class="weather-detail">
                            <span class="weather-label">Wind</span>
                            <span class="weather-value" id="weather-wind">--</span>
                        </div>
                        <div class="weather-detail">
                            <span class="weather-label">Humidity</span>
                            <span class="weather-value" id="weather-humidity">--</span>
                        </div>
                        <div class="weather-detail">
                            <span class="weather-label">Feels</span>
                            <span class="weather-value" id="weather-feel">--</span>
                        </div>
                    </div>
                </div>
            `,
            settings: {
                minWidth: '320px',
                minHeight: '320px'
            },
            editableSettings: [
                { key: 'city', label: 'City Name', type: 'string', value: CONFIG.city },
                { key: 'lat', label: 'Latitude', type: 'string', value: String(CONFIG.lat) },
                { key: 'lon', label: 'Longitude', type: 'string', value: String(CONFIG.lon) },
                {
                    key: 'units',
                    label: 'Units',
                    type: 'select',
                    value: CONFIG.units,
                    options: [
                        { value: 'celsius', label: 'Celsius (°C)' },
                        { value: 'fahrenheit', label: 'Fahrenheit (°F)' }
                    ]
                },
                {
                    key: 'showLocation',
                    label: 'Show Location',
                    type: 'select',
                    value: CONFIG.showLocation,
                    options: [
                        { value: 'show', label: 'Show' },
                        { value: 'hide', label: 'Hide' }
                    ]
                },
                {
                    key: 'showDate',
                    label: 'Show Date',
                    type: 'select',
                    value: CONFIG.showDate,
                    options: [
                        { value: 'show', label: 'Show' },
                        { value: 'hide', label: 'Hide' }
                    ]
                }
            ],
            updateStyle: function (settings) {
                if (settings.city) {
                    CONFIG.city = settings.city;
                    const cityEl = document.getElementById('weather-city');
                    if (cityEl) cityEl.innerText = settings.city;
                }
                if (settings.lat) CONFIG.lat = parseFloat(settings.lat);
                if (settings.lon) CONFIG.lon = parseFloat(settings.lon);
                if (settings.units) CONFIG.units = settings.units;

                if (settings.showLocation) {
                    CONFIG.showLocation = settings.showLocation;
                    const el = document.querySelector('.weather-location');
                    if (el) el.style.display = settings.showLocation === 'hide' ? 'none' : 'flex';
                }

                if (settings.showDate) {
                    CONFIG.showDate = settings.showDate;
                    const el = document.getElementById('weather-date');
                    if (el) el.style.display = settings.showDate === 'hide' ? 'none' : 'block';
                }

                fetchWeather();
            },
            init: function () {
                updateDate();
                fetchWeather();
                refreshInterval = setInterval(fetchWeather, 900000);

            },
            destroy: function () {
                if (refreshInterval) {
                    clearInterval(refreshInterval);
                    refreshInterval = null;
                }
                stopSnow();
            }
        };
    };

    async function fetchWeather() {
        try {
            const tempUnit = CONFIG.units === 'fahrenheit' ? 'fahrenheit' : 'celsius';
            const url = `https://api.open-meteo.com/v1/forecast?latitude=${CONFIG.lat}&longitude=${CONFIG.lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m&temperature_unit=${tempUnit}&timezone=auto`;
            const response = await fetch(url);
            const data = await response.json();
            updateWidget(data.current, data.current_units);
        } catch (error) {
            console.error("Weather fetch failed:", error);
            const condEl = document.getElementById('weather-condition');
            if (condEl) condEl.innerText = "Error Loading";
        }
    }

    function updateWidget(data, units) {
        const cityEl = document.getElementById('weather-city');
        const tempEl = document.getElementById('weather-temp');
        const windEl = document.getElementById('weather-wind');
        const humidityEl = document.getElementById('weather-humidity');
        const feelEl = document.getElementById('weather-feel');
        const condEl = document.getElementById('weather-condition');

        const tempSymbol = units?.temperature_2m || (CONFIG.units === 'fahrenheit' ? '°F' : '°C');

        if (cityEl) cityEl.innerText = CONFIG.city;
        if (tempEl) tempEl.innerText = Math.round(data.temperature_2m) + tempSymbol;
        if (windEl) windEl.innerText = data.wind_speed_10m + " km/h";
        if (humidityEl) humidityEl.innerText = data.relative_humidity_2m + "%";
        if (feelEl) feelEl.innerText = Math.round(data.apparent_temperature) + tempSymbol;

        const weather = getWeatherDescription(data.weather_code);
        if (condEl) condEl.innerText = weather.desc;

        if (weather.isSnow) {
            startSnow();
        } else {
            stopSnow();
        }
    }

    function getWeatherDescription(code) {
        let desc = "Unknown";
        let isSnow = false;

        if (code === 0) desc = "Clear Sky";
        else if (code === 1 || code === 2 || code === 3) desc = "Partly Cloudy";
        else if (code >= 45 && code <= 48) desc = "Foggy";
        else if (code >= 51 && code <= 55) desc = "Drizzle";
        else if (code >= 61 && code <= 67) desc = "Rain";
        else if (code >= 71 && code <= 77) { desc = "Snowfall"; isSnow = true; }
        else if (code >= 80 && code <= 82) desc = "Showers";
        else if (code >= 85 && code <= 86) { desc = "Snow Showers"; isSnow = true; }
        else if (code >= 95) desc = "Thunderstorm";

        return { desc, isSnow };
    }

    function updateDate() {
        const dateEl = document.getElementById('weather-date');
        if (dateEl) {
            const now = new Date();
            dateEl.innerText = now.toLocaleDateString('en-US', {
                weekday: 'short',
                month: 'short',
                day: 'numeric'
            });
        }
    }

    function startSnow() {
        const container = document.getElementById('weather-snow-container');
        if (!container || snowInterval) return;

        snowInterval = setInterval(() => {
            const snowflake = document.createElement('div');
            snowflake.classList.add('weather-snowflake');
            snowflake.style.left = Math.random() * 100 + '%';
            snowflake.style.animationDuration = Math.random() * 3 + 2 + 's';
            snowflake.style.width = snowflake.style.height = Math.random() * 4 + 2 + 'px';
            container.appendChild(snowflake);
            setTimeout(() => snowflake.remove(), 5000);
        }, 200);
    }

    function stopSnow() {
        if (snowInterval) {
            clearInterval(snowInterval);
            snowInterval = null;
            const container = document.getElementById('weather-snow-container');
            if (container) container.innerHTML = '';
        }
    }
})();

