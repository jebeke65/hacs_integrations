# Hierarchical Power Aggregator

Create **hierarchical “total” power/energy sensors** (and chain them) so you can use them in dashboards/cards like **Sankey**.

Each config entry represents a **node** (e.g. `Room A`, `Room Beneden`, `Breaker 3`):

- Select downstream **power sensors** (W) and (optionally) downstream **energy sensors** (kWh/Wh).
- The integration creates:
  - `sensor.<node>_power_total`
  - `sensor.<node>_energy_total` (optional)
- You can use created totals as downstream inputs for other nodes to build a hierarchy.
- Optionally create **proxy (“tagged”) sensors** per downstream power sensor that mirror the original value and add upstream metadata.

## Install (HACS)

1. Add this repository to HACS as a custom repository (**Integration**).
2. Install **Hierarchical Power Aggregator**.
3. Restart Home Assistant.

## Configuration

Settings → Devices & services → Add integration → **Hierarchical Power Aggregator**

### Options (per node)

- **Upstream total sensor (optional)**: choose another node's `*_power_total` (or any sensor) to represent the parent/upstream.
- **Downstream power sensors (W)**
- **Create proxy sensors for downstream power**: creates `sensor.<source>__in_<node>` sensors with attributes:
  - `upstream_node`, `upstream_chain`, `upstream_entity`, `source_entity_id`
- **Enable energy total** + **Downstream energy sensors (kWh/Wh)**

## Notes

- Unknown/unavailable downstream sensors are treated as `0`.
- The integration tries to prevent indirect cycles. If a cycle is detected, totals will show `unavailable` and an attribute `cycle_detected: true`.

