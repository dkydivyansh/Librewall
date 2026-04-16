/*
@name: Live Clock
@author: Dkydivyansh
@description: A minimal and customizable live clock for your desktop.
@min_version: 1
*/

(function () {
  const script = document.currentScript;
  const WIDGET_ID = script.dataset.widgetId;

  const CONFIG = {
    align: "right",

    timeColor: "#ffffff",
    dayColor: "#eaeaea",
  };

  let clockInterval = null;



  function updateClock() {
    const dayNames = [
      "Sunday",
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
      "Friday",
      "Saturday",
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
        timeEl.style.color = CONFIG.timeColor;
        timeEl.style.display = "block";
        timeEl.style.width = "100%";
        timeEl.style.textAlign = CONFIG.align;
      }

      if (dayEl) {
        dayEl.textContent = day;
        dayEl.style.color = CONFIG.dayColor;
        dayEl.style.display = "block";
        dayEl.style.width = "100%";
        dayEl.style.textAlign = CONFIG.align;
      }

      const containerId = WIDGET_ID === "clock" ? "live-clock" : WIDGET_ID;
      const wrapper = document.getElementById(containerId);

      if (wrapper) {
        wrapper.style.textAlign = CONFIG.align;
      }
    } catch (e) {
      console.error(`[Clock Debug] Error in updateClock:`, e);
    }
  }

  window["getWidgetContent_" + WIDGET_ID] = function () {
    const savedStyles =
      typeof WidgetLoader !== "undefined"
        ? WidgetLoader.getStyles(WIDGET_ID)
        : {};
    if (savedStyles.align) CONFIG.align = savedStyles.align;
    if (savedStyles.timeColor) CONFIG.timeColor = savedStyles.timeColor;
    if (savedStyles.dayColor) CONFIG.dayColor = savedStyles.dayColor;

    const isTransparent =
      savedStyles.transparent !== undefined ? savedStyles.transparent : true;

    return {
      id: WIDGET_ID,
      html: `
                <div id="clock-time"></div>
                <div id="clock-day"></div>
            `,
      settings: {
        transparent: isTransparent,
      },
      editableSettings: [
        {
          key: "transparent",
          label: "Transparent Background",
          type: "boolean",
          value: isTransparent,
        },
        {
          key: "align",
          label: "Alignment",
          type: "select",
          value: CONFIG.align,
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
          value: CONFIG.timeColor,
        },
        {
          key: "dayColor",
          label: "Day Color",
          type: "color",
          value: CONFIG.dayColor,
        },
      ],
      updateStyle: function (settings) {
        if (settings.align) CONFIG.align = settings.align;
        if (settings.timeColor) CONFIG.timeColor = settings.timeColor;
        if (settings.dayColor) CONFIG.dayColor = settings.dayColor;
        console.log(`[Clock] Settings updated: align=${CONFIG.align}`);
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
      },
    };
  };
})();
