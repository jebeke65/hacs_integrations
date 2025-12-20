# Hierarchical Power Aggregator

Hierarchical Power Aggregator is a Home Assistant integration that creates **hierarchical “total” power (and optional energy) sensors** by summing the power values of selected downstream sensors — and letting you **chain totals into higher-level nodes** (e.g. device → room → floor → whole house).

This is especially useful for dashboards/cards like **Sankey**, where you want a clear upstream/downstream structure.

* * *

## ✨ Features

✔ Create one config entry per **node** (e.g. `Room A`, `Room Downstairs`, `Circuit Breaker 3`)  
✔ Aggregate downstream **power sensors (W)** into a node total  
✔ Optional **energy total** per node (downstream kWh/Wh → summed to a node energy total)  
✔ Build a **hierarchy** by using a node’s totals as downstream inputs for another node  
✔ Optional **Upstream / parent sensor** reference for each node  
✔ Optional **proxy (“tagged”) sensors** per downstream power sensor, that:
  * mirror the original value
  * add upstream metadata (useful for tracing/visualizing)

✔ Handles missing data:
  * `unknown` / `unavailable` downstream sensors are treated as `0`
✔ Cycle protection:
  * attempts to prevent indirect cycles
  * if a cycle is detected, totals become `unavailable` and expose `cycle_detected: true`

* * *

## Installation via HACS

### Method 1 — HACS Custom Repository

1. Open Home Assistant
2. Go to HACS → Integrations
3. Click the ⋮ menu → Custom repositories
4. Add:

   `https://github.com/jebeke65/hierarchical_power_aggregator`

   Category: **Integration**

5. Install **Hierarchical Power Aggregator**
6. Restart Home Assistant after installation

* * *

## ⚙️ Configuration

After installation:

1. Go to  
   **Settings → Devices & Services → Add Integration**
2. Search for **Hierarchical Power Aggregator**

Each config entry represents a **node**.

### Options (per node)

- **Upstream total sensor** (optional)  
  Choose another node’s `*_power_total` (or any sensor) to represent the parent/upstream.

- **Downstream power sensors (W)**  
  Select the sensors that should be summed into this node’s total.

- **Create proxy sensors for downstream power** (optional)  
  Creates `sensor.<source>__in_<node>` sensors with attributes:
  - `upstream_node`
  - `upstream_chain`
  - `upstream_entity`
  - `source_entity_id`

- **Enable energy total** (optional)  
  Also creates a node energy total, using:
  - **Downstream energy sensors (kWh/Wh)**

### Generated sensors

For each node (example: `Room A`):

- `sensor.room_a_power_total`
- `sensor.room_a_energy_total` *(optional, only when enabled)*

* * *

## 📌 Examples

### Example hierarchy

- Node: `Room A`
  - downstream power: `sensor.pc_power`, `sensor.monitor_power`
- Node: `Floor 1`
  - downstream power: `sensor.room_a_power_total`, `sensor.room_b_power_total`

This lets you build a tree like:

**devices → rooms → floors → whole house**

* * *

## 🧾 Sensor Attributes

Node total sensors expose useful debugging/trace attributes such as:

- `cycle_detected: true` *(only when applicable)*

Proxy (“tagged”) sensors include:

- `upstream_node`
- `upstream_chain`
- `upstream_entity`
- `source_entity_id`

* * *

## 🧠 How it works

The integration:

- Takes your configured nodes
- Reads the selected downstream entities
- Sums downstream power into `*_power_total`
- Optionally sums downstream energy into `*_energy_total`
- Optionally creates proxy sensors per downstream power sensor (for metadata / visualization)
- Checks for cycles and prevents invalid chains where possible

* * *

## 🗺️ Planned Enhancements

- Optional helpers for per-node statistics (daily/weekly/monthly) *(if desired)*

* * *

## Issues / Feature Requests

https://github.com/jebeke65/hierarchical_power_aggregator/issues

* * *

## License

MIT License — see LICENSE file.
