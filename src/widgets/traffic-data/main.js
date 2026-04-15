/*
@name: Traffic Data
@author: Dkydivyansh
@description: Displays real-time network traffic data and usage statistics.
@min_version: 1
*/

(function () {
    const script = document.currentScript;
    const WIDGET_ID = script.dataset.widgetId;

    window['getWidgetContent_' + WIDGET_ID] = function () {
        return {
            id: WIDGET_ID,
            html: `
                <h2>Traffic Data<span id="ws-status"></span></h2>
                <div class="stat-item">
                    <span class="stat-label">Upload:</span>
                    <span class="stat-value" id="upload-speed">...</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Download:</span>
                    <span class="stat-value" id="download-speed">...</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Total Sent:</span>
                    <span class="stat-value" id="total-sent">...</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Total Recv:</span>
                    <span class="stat-value" id="total-recv">...</span>
                </div>
            `,
            settings: {},
            init: function () {
                // Network data is handled by global WebSocket connection
            },
            destroy: function () { }
        };
    };
})();
