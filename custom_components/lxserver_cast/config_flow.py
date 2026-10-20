"""Setup and options UI for LX Server Cast."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_PASSWORD,
    CONF_QUALITY,
    CONF_TARGET,
    CONF_URL,
    CONF_USERNAME,
    CONF_VOLUME,
    DEFAULT_QUALITY,
    DEFAULT_VOLUME,
    DOMAIN,
    QUALITY_OPTIONS,
)
from .lxserver import LxServerAuthError, LxServerClient, LxServerError
from .transport import AiohttpTransport

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): TextSelector(),
        vol.Required(CONF_USERNAME): TextSelector(),
        vol.Required(CONF_PASSWORD): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
    }
)


def _options_schema(current: Mapping[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(CONF_TARGET, description={"suggested_value": current.get(CONF_TARGET)}): EntitySelector(
                EntitySelectorConfig(domain="media_player")
            ),
            vol.Required(CONF_VOLUME, default=current.get(CONF_VOLUME, DEFAULT_VOLUME)): NumberSelector(
                NumberSelectorConfig(min=0, max=1, step=0.05, mode=NumberSelectorMode.SLIDER)
            ),
            vol.Required(CONF_QUALITY, default=current.get(CONF_QUALITY, DEFAULT_QUALITY)): SelectSelector(
                SelectSelectorConfig(options=QUALITY_OPTIONS, mode=SelectSelectorMode.DROPDOWN)
            ),
        }
    )


class LxServerCastConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_URL].strip().rstrip("/")
            username = user_input[CONF_USERNAME].strip()
            password = user_input[CONF_PASSWORD]
            client = LxServerClient(AiohttpTransport(async_get_clientsession(self.hass), url), url, username, password)
            try:
                await client.login()
            except LxServerAuthError:
                errors["base"] = "invalid_auth"
            except LxServerError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"{url}|{username}".lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"lxserver ({username})",
                    data={CONF_URL: url, CONF_USERNAME: username, CONF_PASSWORD: password},
                    options={CONF_VOLUME: DEFAULT_VOLUME, CONF_QUALITY: DEFAULT_QUALITY},
                )
        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: Any) -> LxServerCastOptionsFlow:
        return LxServerCastOptionsFlow()


class LxServerCastOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(step_id="init", data_schema=_options_schema(self.config_entry.options))
