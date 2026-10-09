jQuery(function ($) {
  const chartElement = $("#dailyReportsChart");
  const toggleButtons = $(".daily-reports-chart-mode-toggle button");
  const chartModeStorageKey = "dailyReportsChartMode";
  let url = "daily_reports_chart.json";
  let certname = chartElement.data("certname");
  let days = parseInt(chartElement.data("days"));
  let chartMode = localStorage.getItem(chartModeStorageKey) || chartElement.data("chart-mode") || "stacked";
  let chart = null;
  let chartData = null;
  let defaultJSON = []

  for (let index = days-1; index >= 0; index--) {
    defaultJSON.push({
      day: moment().startOf('day').subtract(index, 'days').format('YYYY-MM-DD'),
      unchanged: 0,
      changed: 0,
      failed: 0
    })
  }

  // Get chart colors from CSS variables (supports dark mode)
  function getChartColors() {
    var style = getComputedStyle(document.documentElement);
    return {
      failed: style.getPropertyValue('--color-failed').trim() || "#AA4643",
      changed: style.getPropertyValue('--color-changed').trim() || "#4572A7",
      unchanged: style.getPropertyValue('--color-unchanged').trim() || "#89A54E",
    };
  }

  function getChartConfig(mode) {
    let splitMode = mode === "split";

    return {
      bindto: "#dailyReportsChart",
      data: {
        json: defaultJSON,
        keys: {
          x: "day",
          value: ["failed", "changed", "unchanged"],
        },
        type: splitMode ? undefined : "bar",
        types: splitMode ? {
          unchanged: "bar",
          changed: "spline",
          failed: "spline",
        } : undefined,
        groups: splitMode ? undefined : [["failed", "changed", "unchanged"]],
        axes: splitMode ? {
          unchanged: "y",
          changed: "y2",
          failed: "y2",
        } : undefined,
        labels: splitMode ? {
          format: function(value, id) {
            if ((id === "changed" || id === "failed") && value > 0 && value < 1000) {
              return Math.round(value);
            }

            return "";
          },
        } : undefined,
        colors: getChartColors(),
      },
      size: {
        height: splitMode ? 220 : 160,
      },
      point: splitMode ? {
        r: 3,
      } : undefined,
      axis: {
        x: {
          type: "category",
        },
        y: splitMode ? {
          label: {
            text: "Unchanged",
            position: "outer-middle",
          },
          tick: {
            format: function(value) { return Math.round(value); },
          },
        } : undefined,
        y2: splitMode ? {
          show: true,
          label: {
            text: "Changed / Failed",
            position: "outer-middle",
          },
          tick: {
            format: function(value) { return Math.round(value); },
          },
        } : undefined,
      },
      legend: {
        show: true,
      },
    };
  }

  function updateModeButtons(mode) {
    toggleButtons.removeClass("active");
    toggleButtons.filter("[data-chart-mode-value='" + mode + "']").addClass("active");
  }

  function renderChart(mode, data) {
    if (chart) {
      chart.destroy();
    }

    chart = bb.generate(getChartConfig(mode));
    chart.load({json: data || defaultJSON});
    updateModeButtons(mode);
  }

  if (typeof certname !== typeof undefined && certname !== false) {
    // truncate /node/certname from URL, to determine path to json
    url =
      window.location.href.replace(/\/node\/[^/]+$/, "") +
      "/daily_reports_chart.json?certname=" +
      certname
  }

  toggleButtons.on("click", function() {
    chartMode = $(this).data("chart-mode-value");
    localStorage.setItem(chartModeStorageKey, chartMode);
    renderChart(chartMode, chartData || defaultJSON);
  });

  renderChart(chartMode, defaultJSON);

  $.getJSON(url, function(data) {
    chartData = data.result;
    renderChart(chartMode, chartData);
  });
})
