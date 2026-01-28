(function () {
    const WIDGET_ID = 'clock';

    const CONFIG = {
        align: 'right',

        timeColor: '#ffffff',
        dayColor: '#eaeaea'
    };

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
            const timeEl = document.getElementById('clock-time');
            const dayEl = document.getElementById('clock-day');

            if (timeEl) {
                timeEl.textContent = timeString;
                timeEl.style.color = CONFIG.timeColor;
            }

            if (dayEl) {
                dayEl.textContent = day;
                dayEl.style.color = CONFIG.dayColor;
            }

            const wrapper = document.getElementById('live-clock');
            if (wrapper) {
                wrapper.style.textAlign = CONFIG.align;
            }
        } catch (e) { }
    }

    let clockInterval = null;

    window.getWidgetContent_clock = function () {

        const savedStyles = typeof WidgetLoader !== 'undefined' ? WidgetLoader.getStyles(WIDGET_ID) : {};
        if (savedStyles.align) CONFIG.align = savedStyles.align;
        if (savedStyles.timeColor) CONFIG.timeColor = savedStyles.timeColor;
        if (savedStyles.dayColor) CONFIG.dayColor = savedStyles.dayColor;

        return {
            id: WIDGET_ID,
            html: `
                <div id="clock-time"></div>
                <div id="clock-day"></div>
            `,
            settings: {},
            editableSettings: [
                {
                    key: 'align',
                    label: 'Alignment',
                    type: 'select',
                    value: CONFIG.align,
                    options: [
                        { value: 'left', label: 'Left' },
                        { value: 'center', label: 'Center' },
                        { value: 'right', label: 'Right' }
                    ]
                },
                { key: 'timeColor', label: 'Time Color', type: 'color', value: CONFIG.timeColor },
                { key: 'dayColor', label: 'Day Color', type: 'color', value: CONFIG.dayColor }
            ],
            updateStyle: function (settings) {
                if (settings.align) CONFIG.align = settings.align;
                if (settings.timeColor) CONFIG.timeColor = settings.timeColor;
                if (settings.dayColor) CONFIG.dayColor = settings.dayColor;
                updateClock();
            },
            init: function () {
                updateClock();
                clockInterval = setInterval(updateClock, 1000);
            },
            destroy: function () {
                if (clockInterval) {
                    clearInterval(clockInterval);
                    clockInterval = null;
                }
            }
        };
    };
})();

