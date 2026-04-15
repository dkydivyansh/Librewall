/*
@name: Listening Ports
@author: Dkydivyansh
@description: Monitors and displays active listening ports on your system.
@min_version: 1
*/

(function () {
    const script = document.currentScript;
    const WIDGET_ID = script.dataset.widgetId;

    window['getWidgetContent_' + WIDGET_ID] = function () {
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
