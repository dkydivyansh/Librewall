/*
@name: Live Traffic Log
@author: Dkydivyansh
@description: Shows a live log of outgoing and incoming network connections.
@min_version: 1
*/

export default class LiveTrafficLogWidget {
  constructor(id) {
    this.id = id;
    this.html = `
            <h2>Live Traffic Log</h2>
            <div id="traffic-log-list" class="net-list">Monitoring...</div>
        `;
    this.settings = {
      minWidth: "650px",
    };
  }

  init() {}
  destroy() {}
}
