
(function () {
    const WIDGET_ID = 'listening-ports';

    window.getWidgetContent_listeningPorts = function () {
        return {
            id: WIDGET_ID,
            html: `
                <h2>Listening Ports <span id="listening-count" class="widget-count"></span></h2>
                <pre id="listening-list">Loading...</pre>
            `,
            settings: {},
            init: function () { },
            destroy: function () { }
        };
    };
})();
