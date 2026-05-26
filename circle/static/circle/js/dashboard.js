/* Renders the dashboard charts from JSON embedded via Django's json_script. */
(function () {
  "use strict";

  const dataEl = document.getElementById("chart-data");
  if (!dataEl || typeof Chart === "undefined") {
    return;
  }

  const data = JSON.parse(dataEl.textContent);

  // Brand palette.
  const CARAMEL = "#C9784B";
  const ESPRESSO = "#1A1A1A";
  const MUTED = "#8B7E74";
  const WARNING = "#D4A845";
  const GRID = "rgba(139, 126, 116, 0.15)";

  Chart.defaults.font.family = "Inter, system-ui, sans-serif";
  Chart.defaults.color = "#2D2826";

  const baseScales = {
    x: { grid: { color: GRID }, ticks: { maxRotation: 0, autoSkip: true } },
    y: { grid: { color: GRID }, beginAtZero: true },
  };

  // 1. Tier distribution (doughnut).
  const tierEl = document.getElementById("tierChart");
  if (tierEl) {
    new Chart(tierEl, {
      type: "doughnut",
      data: {
        labels: data.tier.labels,
        datasets: [
          {
            data: data.tier.data,
            backgroundColor: [CARAMEL, MUTED, WARNING],
            borderColor: "#FAF7F2",
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
        cutout: "62%",
      },
    });
  }

  // 2. Monthly point flow (dual-axis line).
  const monthlyEl = document.getElementById("monthlyChart");
  if (monthlyEl) {
    new Chart(monthlyEl, {
      type: "line",
      data: {
        labels: data.monthly.labels,
        datasets: [
          {
            label: "Earned",
            data: data.monthly.earned,
            borderColor: CARAMEL,
            backgroundColor: "rgba(201, 120, 75, 0.1)",
            fill: true,
            tension: 0.3,
            yAxisID: "y",
          },
          {
            label: "Redeemed",
            data: data.monthly.redeemed,
            borderColor: ESPRESSO,
            backgroundColor: "rgba(26, 26, 26, 0.05)",
            fill: false,
            tension: 0.3,
            yAxisID: "y1",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: { legend: { position: "bottom" } },
        scales: {
          x: baseScales.x,
          y: {
            type: "linear",
            position: "left",
            beginAtZero: true,
            grid: { color: GRID },
            title: { display: true, text: "Earned" },
          },
          y1: {
            type: "linear",
            position: "right",
            beginAtZero: true,
            grid: { drawOnChartArea: false },
            title: { display: true, text: "Redeemed" },
          },
        },
      },
    });
  }

  // 3. Points by earn source (horizontal bar).
  const sourceEl = document.getElementById("sourceChart");
  if (sourceEl) {
    new Chart(sourceEl, {
      type: "bar",
      data: {
        labels: data.source.labels,
        datasets: [
          {
            label: "Points",
            data: data.source.data,
            backgroundColor: CARAMEL,
            borderRadius: 4,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: GRID }, beginAtZero: true },
          y: { grid: { display: false } },
        },
      },
    });
  }

  // 4. Daily transactions with 7-day rolling average (line).
  const dailyEl = document.getElementById("dailyChart");
  if (dailyEl) {
    new Chart(dailyEl, {
      type: "line",
      data: {
        labels: data.daily.labels,
        datasets: [
          {
            label: "7-day average",
            data: data.daily.rolling,
            borderColor: CARAMEL,
            backgroundColor: "rgba(201, 120, 75, 0.12)",
            fill: true,
            tension: 0.35,
            pointRadius: 0,
            borderWidth: 2,
          },
          {
            label: "Daily count",
            data: data.daily.counts,
            borderColor: MUTED,
            borderWidth: 1,
            pointRadius: 0,
            fill: false,
            tension: 0.2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: { legend: { position: "bottom" } },
        scales: baseScales,
      },
    });
  }
})();
