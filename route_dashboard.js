(() => {
  const byId = id => document.getElementById(id);
  const form = byId("route-form");
  const fields = byId("route-fields");
  const scenario = byId("route-scenario");
  const stopList = byId("route-destinations");
  const status = byId("route-status");
  const palette = ["#fbbf24", "#818cf8", "#2dd4bf"];
  const algorithms = [
    ["original", "Original"], ["nearest_neighbour", "Nearest Neighbour"],
    ["genetic_algorithm", "Genetic Algorithm"],
  ];
  const metrics = [
    ["distance_km", "Distance (km)", 2], ["travel_hours", "Travel time (h)", 2],
    ["cost", "Estimated cost (INR)", 2], ["fitness", "Weighted fitness", 5],
    ["runtime_ms", "Runtime (ms)", 3],
  ];
  const vehicleFields = [
    ["capacity", "Vehicle capacity (units)", 1, 1000000, 1],
    ["cost_per_km", "Cost (INR/km)", 0, 100000, "any"],
    ["speed_kph", "Average speed (km/h)", 1, 200, "any"],
  ];
  const gaFields = [
    ["population_size", "Population size", 2, 200, 1], ["generations", "Generations", 1, 400, 1],
    ["mutation_probability", "Mutation probability", 0, 1, "any"],
    ["crossover_probability", "Crossover probability", 0, 1, "any"],
    ["elite_count", "Elite count", 1, 199, 1], ["seed", "Random seed", 0, 4294967295, 1],
    ["distance", "Distance weight", 0, 1, "any"], ["time", "Time weight", 0, 1, "any"],
    ["cost", "Cost weight", 0, 1, "any"],
  ];

  let warehouse, loadedScenario, result, map, layers, convergence, bars;
  let ready = false;
  let stopId = 0;

  function node(tag, content, className) {
    const item = document.createElement(tag);
    if (content !== undefined) item.textContent = content;
    if (className) item.className = className;
    return item;
  }

  function input(definition, value) {
    const [key, text, min, max, step] = definition;
    const label = node("label", text);
    const field = node("input", undefined, "dark-input");
    field.name = key;
    field.required = true;
    field.value = value;
    if (step !== undefined) {
      Object.assign(field, {type: "number", min, max, step});
    } else {
      field.maxLength = max;
    }
    label.append(field);
    return label;
  }

  function reindexStops() {
    const rows = [...stopList.children];
    rows.forEach((row, index) => {
      row.querySelector("strong").textContent = "Stop " + (index + 1);
      row.querySelector('[data-move="up"]').disabled = index === 0;
      row.querySelector('[data-move="down"]').disabled = index === rows.length - 1;
      row.querySelector('[data-move="remove"]').disabled = rows.length <= 3;
    });
    byId("route-add").disabled = rows.length >= 15;
  }

  function addStop(stop = {id: "custom-" + (++stopId), name: "", latitude: "", longitude: "", demand: 1, priority: "standard"}) {
    const row = node("div", undefined, "route-stop");
    row.dataset.id = stop.id;
    row.dataset.priority = stop.priority;
    const controls = node("div", undefined, "route-controls mb-2");
    controls.append(node("strong"));
    [["up", "↑", "Move earlier"], ["down", "↓", "Move later"], ["remove", "Remove", "Remove stop"]]
      .forEach(([action, text, label]) => {
        const button = node("button", text, "route-btn");
        button.type = "button";
        button.dataset.move = action;
        button.setAttribute("aria-label", label);
        controls.append(button);
      });
    const grid = node("div", undefined, "route-grid");
    const definitions = [
      ["name", "Destination name", 1, 100], ["latitude", "Latitude", -90, 90, "any"],
      ["longitude", "Longitude", -180, 180, "any"], ["demand", "Demand (units)", 1, 1000000, 1],
    ];
    definitions.forEach(definition => grid.append(input(definition, stop[definition[0]])));
    row.append(controls, grid);
    stopList.append(row);
    reindexStops();
  }

  async function request(path, body) {
    const response = await fetch(API("/route" + path), body === undefined ? undefined : {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(payload.detail)
        ? payload.detail.map(item => item.loc.slice(1).join(".") + " " + item.msg).join(" · ")
        : payload.detail;
      throw new Error(detail || "Routing request failed");
    }
    return payload;
  }

  function clearResult() {
    result = null;
    byId("route-results").classList.add("hidden");
  }

  function populate(data) {
    warehouse = data.warehouse;
    byId("route-warehouse").textContent =
      warehouse.name + " warehouse · " + warehouse.latitude + ", " + warehouse.longitude + " · Synthetic academic scenario";
    byId("route-vehicle").replaceChildren(...vehicleFields.map(definition => input(definition, data[definition[0]])));
    const values = {...data.parameters, ...data.weights};
    byId("route-parameters").replaceChildren(...gaFields.map(definition => input(definition, values[definition[0]])));
    stopList.replaceChildren();
    data.destinations.forEach(addStop);
    clearResult();
  }

  async function run(message, action) {
    fields.disabled = true;
    status.textContent = message;
    status.classList.remove("text-red-300");
    try {
      await action();
    } catch (error) {
      status.textContent = error.message + " · Check the inputs and confirm the local API is running.";
      status.classList.add("text-red-300");
    } finally {
      fields.disabled = false;
    }
  }

  async function loadSample() {
    const selected = scenario.value;
    if (!selected) throw new Error("Select a sample scenario");
    populate(await request("/sample?scenario=" + encodeURIComponent(selected)));
    loadedScenario = selected;
    status.textContent = "Scenario loaded.";
  }

  function formValues(container) {
    return Object.fromEntries([...container.querySelectorAll("input")].map(field => [
      field.name, field.type === "number" ? field.valueAsNumber : field.value.trim(),
    ]));
  }

  function payload() {
    const {distance, time, cost, ...parameters} = formValues(byId("route-parameters"));
    return {
      warehouse, ...formValues(byId("route-vehicle")), parameters, weights: {distance, time, cost},
      destinations: [...stopList.children].map(row => ({
        id: row.dataset.id, priority: row.dataset.priority, ...formValues(row),
      })),
    };
  }

  const format = (value, digits = 2) => Number(value).toLocaleString(undefined, {maximumFractionDigits: digits});
  const sequenceText = sequence => sequence.map(index => result.locations[index].name).join(" → ");

  function renderMap() {
    if (!window.L) {
      byId("route-map").textContent = "Leaflet could not load. The route sequences are available below.";
      return;
    }
    if (!map) {
      map = L.map("route-map");
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(map);
      layers = L.layerGroup().addTo(map);
    }
    layers.clearLayers();
    const coordinates = result.locations.map(location => [location.latitude, location.longitude]);
    const optimized = result.genetic_algorithm.sequence;
    L.polyline(optimized.map(index => coordinates[index]), {color: "#0f766e", weight: 6}).addTo(layers);
    L.polyline(result.original.sequence.map(index => coordinates[index]), {
      color: "#b45309", weight: 3, dashArray: "7 9",
    }).addTo(layers);
    coordinates.forEach((point, index) => {
      const location = result.locations[index];
      const number = index ? optimized.indexOf(index) : "W";
      const popup = node("div");
      popup.append(node("strong", location.name));
      popup.append(node("p", index
        ? "Optimized stop " + number + " · Original stop " + result.original.sequence.indexOf(index)
          + " · " + location.demand + " units · Priority: " + location.priority
        : "Warehouse · " + result.demand + " / " + result.capacity + " units"));
      L.marker(point, {
        title: location.name,
        icon: L.divIcon({className: "route-map-pin" + (index ? "" : " depot"), html: String(number), iconSize: [28, 28]}),
      }).bindPopup(popup).addTo(layers);
    });
    map.invalidateSize();
    map.fitBounds(coordinates, {padding: [24, 24], maxZoom: 14});
  }

  function renderCharts() {
    if (!window.Chart) {
      status.textContent += " Chart.js could not load.";
      return;
    }
    convergence?.destroy();
    bars?.destroy();
    const chartOptions = (x, y) => ({
      maintainAspectRatio: false,
      plugins: {legend: {labels: {color: "#e5e7eb"}}},
      scales: Object.fromEntries([["x", x], ["y", y]].map(([axis, title]) => [axis, {
        title: {display: true, text: title, color: "#e5e7eb"},
        ticks: {color: "#d1d5db", maxTicksLimit: 12}, grid: {color: "#343541"},
      }])),
    });
    convergence = new Chart(byId("route-convergence"), {
      type: "line", options: chartOptions("Generation", "Weighted fitness"),
      data: {
        labels: result.convergence.map(row => row.generation),
        datasets: [
          {label: "Best fitness", data: result.convergence.map(row => row.best), borderColor: palette[2], pointRadius: 0},
          {label: "Average fitness", data: result.convergence.map(row => row.average), borderColor: palette[1], pointRadius: 0},
        ],
      },
    });
    bars = new Chart(byId("route-bars"), {
      type: "bar", options: chartOptions("Algorithm", "Estimated distance (km)"),
      data: {
        labels: algorithms.map(([, label]) => label),
        datasets: [{label: "Distance (km)", backgroundColor: palette, data: algorithms.map(([key]) => result[key].distance_km)}],
      },
    });
  }

  function render() {
    const ga = result.genetic_algorithm;
    const savings = result.savings;
    const cards = [
      ["Original distance", format(result.original.distance_km) + " km"],
      ["Optimized distance", format(ga.distance_km) + " km"],
      ["Distance saved", format(savings.distance_km) + " km"],
      ["Estimated time saved", format(savings.travel_hours * 60) + " min"],
      ["Estimated cost saved", "INR " + format(savings.cost)],
      ["Distance improvement", savings.distance_pct === null ? "—" : format(savings.distance_pct) + "%"],
      ["GA execution time", format(ga.runtime_ms) + " ms"],
    ];
    byId("route-kpis").replaceChildren(...cards.map(([label, value]) => {
      const card = node("div", label, "route-kpi");
      card.append(node("strong", value));
      return card;
    }));
    byId("route-gap").textContent = result.exact
      ? "Exact benchmark fitness " + format(result.exact.fitness, 5) + " · GA optimality gap " + (result.optimality_gap_pct === null ? "undefined (zero optimum)" : format(result.optimality_gap_pct, 5) + "%")
      : "Exact comparison is available for tours of up to 10 destinations.";
    byId("route-comparison").replaceChildren(...metrics.map(([key, label, digits]) => {
      const row = node("tr");
      const heading = node("th", label);
      heading.scope = "row";
      row.append(heading, ...algorithms.map(([algorithm]) => node("td", format(result[algorithm][key], digits))));
      return row;
    }));
    byId("route-sequences").replaceChildren(...algorithms.map(([key, label]) => {
      const sequence = node("p");
      sequence.append(node("strong", label + " · "), document.createTextNode(sequenceText(result[key].sequence)));
      return sequence;
    }));
    byId("route-map-note").textContent = result.model.label + " · Straight-line map links. "
      + "Estimated driving distance uses a " + result.model.driving_factor + "× Haversine factor. "
      + "Time and cost scale with distance in this simulation.";
    byId("route-results").classList.remove("hidden");
    renderMap();
    renderCharts();
  }

  function download(name, content, type) {
    const url = URL.createObjectURL(new Blob([content], {type}));
    const anchor = node("a");
    anchor.download = name;
    anchor.href = url;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function csvCell(value) {
    let text = String(value ?? "");
    if (typeof value === "string" && /^[\s]*[=+\-@]/.test(text)) text = "'" + text;
    return '"' + text.replaceAll('"', '""') + '"';
  }

  byId("route-json").onclick = () => {
    if (result) download("predict-route.json", JSON.stringify(result, null, 2), "application/json");
  };
  byId("route-csv").onclick = () => {
    if (!result) return;
    const rows = [["Algorithm", ...metrics.map(([, label]) => label), "Sequence"]];
    for (const [key, label] of [...algorithms, ["exact", "Exact"]]) {
      const route = result[key];
      if (route) rows.push([label, ...metrics.map(([metric]) => route[metric]), sequenceText(route.sequence)]);
    }
    download("predict-route.csv", rows.map(row => row.map(csvCell).join(",")).join("\r\n"), "text/csv;charset=utf-8");
  };

  byId("route-load").onclick = () => run("Loading scenario…", loadSample);
  byId("route-reset").onclick = () => run("Resetting configuration…", async () => {
    if (loadedScenario) scenario.value = loadedScenario;
    await loadSample();
  });
  byId("route-add").onclick = () => { addStop(); clearResult(); };
  stopList.addEventListener("click", event => {
    const action = event.target.dataset.move;
    if (!action) return;
    const row = event.target.closest(".route-stop");
    if (action === "up" && row.previousElementSibling) row.previousElementSibling.before(row);
    if (action === "down" && row.nextElementSibling) row.nextElementSibling.after(row);
    if (action === "remove") row.remove();
    reindexStops();
    clearResult();
  });
  form.addEventListener("input", event => { if (event.target !== scenario) clearResult(); });
  form.addEventListener("invalid", event => {
    const details = event.target.closest("details");
    if (details) details.open = true;
  }, true);
  form.addEventListener("submit", event => {
    event.preventDefault();
    if (!warehouse) {
      status.textContent = "Load a sample scenario first.";
      return;
    }
    clearResult();
    run("Optimizing delivery sequence…", async () => {
      result = await request("/optimize", payload());
      status.textContent = "Optimization complete.";
      render();
    });
  });

  document.querySelector('[data-page="route"]').addEventListener("click", () => {
    if (ready) {
      if (result) requestAnimationFrame(() => map?.invalidateSize());
      return;
    }
    run("Loading route settings…", async () => {
      const config = await request("/config");
      scenario.replaceChildren(...config.scenarios.map(item => {
        const option = node("option", item.warehouse.name + " · " + item.destination_count + " stops");
        option.value = item.id;
        return option;
      }));
      ready = true;
      status.textContent = "Select Load Sample Scenario to begin.";
    });
  });
})();
