/*
@name: Live Clock
@author: Dkydivyansh
@description: A minimal and customizable live clock for your desktop.
@min_version: 1
*/

export default class ClockWidget {
  constructor(WIDGET_ID) {
    this.id = WIDGET_ID;
    
    // Config properties
    this.align = "right";
    this.timeColor = "#ffffff";
    this.dayColor = "#eaeaea";
    this.transparent = true;

    // Load saved styles
    const savedStyles = typeof WidgetLoader !== "undefined" ? WidgetLoader.getStyles(this.id) : {};
    if (savedStyles.align !== undefined) this.align = savedStyles.align;
    if (savedStyles.timeColor !== undefined) this.timeColor = savedStyles.timeColor;
    if (savedStyles.dayColor !== undefined) this.dayColor = savedStyles.dayColor;
    if (savedStyles.transparent !== undefined) this.transparent = savedStyles.transparent;

    this.html = `
        <div id="clock-time"></div>
        <div id="clock-day"></div>
    `;

    this.settings = {
        transparent: this.transparent
    };

    this.editableSettings = [
        {
          key: "transparent",
          label: "Transparent Background",
          type: "boolean",
          value: this.transparent,
        },
        {
          key: "align",
          label: "Alignment",
          type: "select",
          value: this.align,
          options: [
            { value: "left", label: "Left" },
            { value: "center", label: "Center" },
            { value: "right", label: "Right" },
          ],
        },
        {
          key: "timeColor",
          label: "Time Color",
          type: "color",
          value: this.timeColor,
        },
        {
          key: "dayColor",
          label: "Day Color",
          type: "color",
          value: this.dayColor,
        },
    ];

    this.clockInterval = null;
    this.updateClock = this.updateClock.bind(this);
  }

  updateClock() {
    const dayNames = [
      "Sunday", "Monday", "Tuesday", "Wednesday",
      "Thursday", "Friday", "Saturday"
    ];
    const now = new Date();
    let hours = now.getHours();
    let minutes = now.getMinutes();
    let seconds = now.getSeconds();
    const day = dayNames[now.getDay()];
    const ampm = hours >= 12 ? "PM" : "AM";

    hours = hours % 12;
    hours = hours ? hours : 12;
    hours = hours < 10 ? "0" + hours : hours;
    minutes = minutes < 10 ? "0" + minutes : minutes;
    seconds = seconds < 10 ? "0" + seconds : seconds;

    const timeString = `${hours}:${minutes}:${seconds} ${ampm}`;

    try {
      const timeEl = document.getElementById("clock-time");
      const dayEl = document.getElementById("clock-day");

      if (timeEl) {
        timeEl.textContent = timeString;
        timeEl.style.color = this.timeColor;
        timeEl.style.display = "block";
        timeEl.style.width = "100%";
        timeEl.style.textAlign = this.align;
      }

      if (dayEl) {
        dayEl.textContent = day;
        dayEl.style.color = this.dayColor;
        dayEl.style.display = "block";
        dayEl.style.width = "100%";
        dayEl.style.textAlign = this.align;
      }

      const containerId = this.id === "clock" ? "live-clock" : this.id;
      const wrapper = document.getElementById(containerId);

      if (wrapper) {
        wrapper.style.textAlign = this.align;
      }
    } catch (e) {
      console.error(`[Clock Debug] Error in updateClock:`, e);
    }
  }

  updateStyle(settings) {
    if (settings.align !== undefined) this.align = settings.align;
    if (settings.timeColor !== undefined) this.timeColor = settings.timeColor;
    if (settings.dayColor !== undefined) this.dayColor = settings.dayColor;
    this.updateClock();
  }

  init() {
    this.updateClock();
    this.clockInterval = setInterval(this.updateClock, 1000);
  }

  destroy() {
    if (this.clockInterval) {
      clearInterval(this.clockInterval);
      this.clockInterval = null;
    }
  }
}
