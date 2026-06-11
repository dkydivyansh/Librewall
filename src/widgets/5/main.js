/*
@name: Listening Ports
@author: Dkydivyansh
@description: Monitors and displays active listening ports on your system.
@min_version: 10
*/

export default class ListeningPortsWidget {
  constructor(id) {
    this.id = id;
    this.html = `
            <h2>Listening Ports <span id="listening-count" class="widget-count"></span></h2>
            <div id="listening-ports-list" class="net-list">Loading...</div>
        `;
    this.settings = {};
    this.modules = ["listening_count"];
  }

  init() { }
  destroy() { }
}
