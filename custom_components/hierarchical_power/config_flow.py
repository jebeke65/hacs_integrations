from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_NODE_NAME,
    CONF_DOWNSTREAM_POWER,
    CONF_ENABLE_ENERGY,
    CONF_DOWNSTREAM_ENERGY,
    CONF_UPSTREAM_ENTITY,
    CONF_CREATE_PROXIES,
)

DEFAULT_ENABLE_ENERGY = False
DEFAULT_CREATE_PROXIES = False


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "node"


class HierarchicalPowerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            node_name = user_input[CONF_NODE_NAME].strip()
            if not node_name:
                errors[CONF_NODE_NAME] = "required"
            else:
                slug = _slugify(node_name)
                await self.async_set_unique_id(slug)
                self._abort_if_unique_id_configured()

                data = {
                    CONF_NODE_NAME: node_name,
                }
                options = {
                    CONF_UPSTREAM_ENTITY: user_input.get(CONF_UPSTREAM_ENTITY),
                    CONF_DOWNSTREAM_POWER: user_input.get(CONF_DOWNSTREAM_POWER, []),
                    CONF_CREATE_PROXIES: bool(user_input.get(CONF_CREATE_PROXIES, DEFAULT_CREATE_PROXIES)),
                    CONF_ENABLE_ENERGY: bool(user_input.get(CONF_ENABLE_ENERGY, DEFAULT_ENABLE_ENERGY)),
                    CONF_DOWNSTREAM_ENERGY: user_input.get(CONF_DOWNSTREAM_ENERGY, []),
                }

                return self.async_create_entry(title=node_name, data=data, options=options)

        schema = vol.Schema(
            {
                vol.Required(CONF_NODE_NAME): str,
                vol.Optional(CONF_UPSTREAM_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"], multiple=False)
                ),
                vol.Optional(CONF_DOWNSTREAM_POWER, default=[]): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"], multiple=True)
                ),
                vol.Optional(CONF_CREATE_PROXIES, default=DEFAULT_CREATE_PROXIES): bool,
                vol.Optional(CONF_ENABLE_ENERGY, default=DEFAULT_ENABLE_ENERGY): bool,
                vol.Optional(CONF_DOWNSTREAM_ENERGY, default=[]): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"], multiple=True)
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return HierarchicalPowerOptionsFlowHandler(config_entry)


class HierarchicalPowerOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_UPSTREAM_ENTITY: user_input.get(CONF_UPSTREAM_ENTITY),
                    CONF_DOWNSTREAM_POWER: user_input.get(CONF_DOWNSTREAM_POWER, []),
                    CONF_CREATE_PROXIES: bool(user_input.get(CONF_CREATE_PROXIES, DEFAULT_CREATE_PROXIES)),
                    CONF_ENABLE_ENERGY: bool(user_input.get(CONF_ENABLE_ENERGY, DEFAULT_ENABLE_ENERGY)),
                    CONF_DOWNSTREAM_ENERGY: user_input.get(CONF_DOWNSTREAM_ENERGY, []),
                },
            )

        o = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(CONF_UPSTREAM_ENTITY, default=o.get(CONF_UPSTREAM_ENTITY)): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"], multiple=False)
                ),
                vol.Optional(CONF_DOWNSTREAM_POWER, default=o.get(CONF_DOWNSTREAM_POWER, [])): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"], multiple=True)
                ),
                vol.Optional(CONF_CREATE_PROXIES, default=o.get(CONF_CREATE_PROXIES, DEFAULT_CREATE_PROXIES)): bool,
                vol.Optional(CONF_ENABLE_ENERGY, default=o.get(CONF_ENABLE_ENERGY, DEFAULT_ENABLE_ENERGY)): bool,
                vol.Optional(CONF_DOWNSTREAM_ENERGY, default=o.get(CONF_DOWNSTREAM_ENERGY, [])): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"], multiple=True)
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
