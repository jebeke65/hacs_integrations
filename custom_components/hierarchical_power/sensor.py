from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DOMAIN,
    CONF_NODE_NAME,
    CONF_DOWNSTREAM_POWER,
    CONF_ENABLE_ENERGY,
    CONF_DOWNSTREAM_ENERGY,
    CONF_UPSTREAM_ENTITY,
    CONF_CREATE_PROXIES,
    DEFAULT_UNIT_POWER,
    DEFAULT_UNIT_ENERGY,
)


def _safe_float(state: Any) -> float:
    try:
        return float(state)
    except (TypeError, ValueError):
        return 0.0


def _get_uom(hass: HomeAssistant, entity_id: str) -> Optional[str]:
    st = hass.states.get(entity_id)
    if not st:
        return None
    return st.attributes.get("unit_of_measurement")


def _energy_to_kwh(value: float, uom: Optional[str]) -> float:
    if uom is None:
        return value
    if uom.lower() == "wh":
        return value / 1000.0
    return value


@dataclass(frozen=True)
class NodeConfig:
    name: str
    upstream_entity: Optional[str]
    downstream_power: list[str]
    enable_energy: bool
    downstream_energy: list[str]
    create_proxies: bool


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    o = entry.options
    node = NodeConfig(
        name=entry.data[CONF_NODE_NAME],
        upstream_entity=o.get(CONF_UPSTREAM_ENTITY),
        downstream_power=list(o.get(CONF_DOWNSTREAM_POWER, [])),
        enable_energy=bool(o.get(CONF_ENABLE_ENERGY, False)),
        downstream_energy=list(o.get(CONF_DOWNSTREAM_ENERGY, [])),
        create_proxies=bool(o.get(CONF_CREATE_PROXIES, False)),
    )

    entities: list[SensorEntity] = []
    power_total = AggregatedPowerTotalSensor(hass, entry, node)
    entities.append(power_total)

    if node.enable_energy and node.downstream_energy:
        entities.append(AggregatedEnergyTotalSensor(hass, entry, node))

    if node.create_proxies:
        # one proxy per downstream power sensor
        for src in node.downstream_power:
            entities.append(ProxyTaggedSensor(hass, entry, node, source_entity_id=src))

    async_add_entities(entities, update_before_add=True)


def _detect_cycle(hass: HomeAssistant, start_entity_id: str) -> bool:
    """Detect cycles by following upstream_entity chain via entity attributes.

    We assume upstream nodes are represented by sensors that have attribute 'upstream_entity'
    (set by this integration). If following the chain reaches start_entity_id again -> cycle.
    """
    seen: set[str] = set()
    current = start_entity_id
    while current:
        if current in seen:
            return True
        seen.add(current)
        st = hass.states.get(current)
        if not st:
            return False
        nxt = st.attributes.get("upstream_entity")
        if not nxt:
            return False
        current = nxt
    return False


def _build_chain(hass: HomeAssistant, upstream_entity: Optional[str], max_depth: int = 12) -> str:
    parts: list[str] = []
    cur = upstream_entity
    depth = 0
    while cur and depth < max_depth:
        st = hass.states.get(cur)
        if not st:
            parts.append(cur)
            break
        parts.append(st.name)
        cur = st.attributes.get("upstream_entity")
        depth += 1
    return " > ".join(parts)


class _BaseNodeSensor(SensorEntity):
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, node: NodeConfig) -> None:
        self.hass = hass
        self.entry = entry
        self.node = node
        self._unsub = None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=node.name,
            manufacturer="Custom",
            model="Hierarchical aggregator node",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _handle_event(event) -> None:
            self.async_write_ha_state()

        watch = set(self._watched_entities())
        if watch:
            self._unsub = async_track_state_change_event(self.hass, list(watch), _handle_event)

    def _watched_entities(self) -> list[str]:
        return []

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None
        await super().async_will_remove_from_hass()


class AggregatedPowerTotalSensor(_BaseNodeSensor):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:flash"
    _attr_native_unit_of_measurement = DEFAULT_UNIT_POWER

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, node: NodeConfig) -> None:
        super().__init__(hass, entry, node)
        self._attr_unique_id = f"{entry.unique_id}_power_total"
        self._attr_name = f"{node.name} Power total"

    def _watched_entities(self) -> list[str]:
        # watch downstream + upstream chain for attribute changes + own id for cycle check
        return list(self.node.downstream_power) + ([self.node.upstream_entity] if self.node.upstream_entity else [])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        chain = _build_chain(self.hass, self.node.upstream_entity)
        cycle = self.entity_id is not None and _detect_cycle(self.hass, self.entity_id)
        return {
            "downstream_entities": list(self.node.downstream_power),
            "upstream_entity": self.node.upstream_entity,
            "upstream_chain": chain,
            "cycle_detected": cycle,
        }

    @property
    def available(self) -> bool:
        if self.entity_id and _detect_cycle(self.hass, self.entity_id):
            return False
        return True

    @property
    def native_value(self) -> float:
        total = 0.0
        for ent_id in self.node.downstream_power:
            if self.entity_id and ent_id == self.entity_id:
                continue
            st = self.hass.states.get(ent_id)
            if not st:
                continue
            total += _safe_float(st.state)
        return round(total, 3)


class AggregatedEnergyTotalSensor(_BaseNodeSensor):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:lightning-bolt"
    _attr_native_unit_of_measurement = DEFAULT_UNIT_ENERGY

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, node: NodeConfig) -> None:
        super().__init__(hass, entry, node)
        self._attr_unique_id = f"{entry.unique_id}_energy_total"
        self._attr_name = f"{node.name} Energy total"

    def _watched_entities(self) -> list[str]:
        return list(self.node.downstream_energy) + ([self.node.upstream_entity] if self.node.upstream_entity else [])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        chain = _build_chain(self.hass, self.node.upstream_entity)
        return {
            "downstream_entities": list(self.node.downstream_energy),
            "upstream_entity": self.node.upstream_entity,
            "upstream_chain": chain,
        }

    @property
    def native_value(self) -> float:
        total_kwh = 0.0
        for ent_id in self.node.downstream_energy:
            st = self.hass.states.get(ent_id)
            if not st:
                continue
            uom = st.attributes.get("unit_of_measurement")
            total_kwh += _energy_to_kwh(_safe_float(st.state), uom)
        return round(total_kwh, 6)


class ProxyTaggedSensor(_BaseNodeSensor):
    """Mirror a source sensor value and add upstream metadata."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, node: NodeConfig, source_entity_id: str) -> None:
        super().__init__(hass, entry, node)
        self.source_entity_id = source_entity_id
        # unique id derived from entry + source
        safe_src = source_entity_id.replace(".", "_")
        self._attr_unique_id = f"{entry.unique_id}_proxy_{safe_src}"
        self._attr_name = f"{source_entity_id} ({node.name})"
        self._attr_icon = "mdi:tag"

    def _watched_entities(self) -> list[str]:
        return [self.source_entity_id, self.node.upstream_entity] if self.node.upstream_entity else [self.source_entity_id]

    @property
    def device_class(self):
        st = self.hass.states.get(self.source_entity_id)
        if not st:
            return None
        return st.attributes.get("device_class")

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        return _get_uom(self.hass, self.source_entity_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "source_entity_id": self.source_entity_id,
            "upstream_node": self.node.name,
            "upstream_entity": self.node.upstream_entity,
            "upstream_chain": _build_chain(self.hass, self.node.upstream_entity),
        }

    @property
    def native_value(self) -> float:
        st = self.hass.states.get(self.source_entity_id)
        if not st:
            return 0.0
        return _safe_float(st.state)
