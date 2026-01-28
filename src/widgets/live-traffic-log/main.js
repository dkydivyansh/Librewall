
(function () {
    const WIDGET_ID = 'live-traffic-log';

    window.getWidgetContent_liveTrafficLog = function () {
        return {
            id: WIDGET_ID,
            html: `
                <h2>Live Traffic Log</h2>
                <pre id="traffic-log-list">Monitoring...</pre>
            `,
            settings: {},
            init: function () { },
            destroy: function () { }
        };
    };
})();
