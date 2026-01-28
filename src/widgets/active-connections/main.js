
(function () {
    const WIDGET_ID = 'active-connections';

    window.getWidgetContent_activeConnections = function () {
        return {
            id: WIDGET_ID,
            html: `
                <h2>Active Connections <span id="active-count" class="widget-count"></span></h2>
                <pre id="active-list">Loading...</pre>
            `,
            settings: {},
            init: function () { },
            destroy: function () { }
        };
    };
})();
