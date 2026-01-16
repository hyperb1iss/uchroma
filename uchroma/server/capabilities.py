#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

"""Device capability detection and querying."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .effects import Effects
from .hardware import Capability

if TYPE_CHECKING:
    from .device_base import BaseUChromaDevice


@dataclass
class DeviceCapabilities:
    """
    Runtime capability detection for devices.

    Provides methods to query what features a device supports,
    combining static configuration data with runtime detection.
    """

    device: BaseUChromaDevice
    _tested_effects: dict[str, bool] = field(default_factory=dict)

    # ─────────────────────────────────────────────────────────────────────────
    # LED/Matrix Capabilities
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def has_leds(self) -> bool:
        """
        True if device has any RGB LEDs.

        Checks the NO_LED capability/quirk and supported_leds list.

        :return: True if device has LEDs
        """
        if self.device.hardware.has_capability(Capability.NO_LED):
            return False
        return self.device.hardware.has_leds

    @property
    def has_matrix(self) -> bool:
        """
        True if device has an addressable LED matrix.

        :return: True if device has a 2D LED matrix
        """
        return self.device.has_matrix

    @property
    def is_single_led(self) -> bool:
        """
        True if device has only a single LED zone.

        :return: True if device has exactly one LED
        """
        return self.device.hardware.has_capability(Capability.SINGLE_LED)

    @property
    def matrix_dimensions(self) -> tuple[int, int] | None:
        """
        Get matrix dimensions as (height, width).

        :return: Tuple of (height, width) or None if no matrix
        """
        dims = self.device.hardware.dimensions
        if dims is None:
            return None
        return (dims.y, dims.x)

    # ─────────────────────────────────────────────────────────────────────────
    # Effect Capabilities
    # ─────────────────────────────────────────────────────────────────────────

    def has_hardware_effect(self, effect_name: str) -> bool:
        """
        Test if device supports a specific hardware effect.

        Checks the static configuration first, then caches the result.

        :param effect_name: Name of the effect to check
        :return: True if the effect is supported
        """
        effect_lower = effect_name.lower()

        if effect_lower in self._tested_effects:
            return self._tested_effects[effect_lower]

        # Check device's hardware_effects or supported_fx list
        result = self.device.hardware.supports_effect(effect_lower)
        self._tested_effects[effect_lower] = result
        return result

    @property
    def requires_software_effects(self) -> bool:
        """
        True if device needs software-rendered effects.

        Some devices have no firmware effects and require software
        rendering of all lighting patterns.

        :return: True if software effects are required
        """
        return self.device.hardware.has_capability(Capability.SOFTWARE_EFFECTS)

    @property
    def supported_effects(self) -> set[str]:
        """
        Get set of supported hardware effect names.

        :return: Set of effect names (lowercase)
        """
        effects = self.device.hardware.get_supported_effects()
        if effects:
            return set(effects)

        # If no explicit list, return effects supported by the protocol
        uses_extended = self.device.hardware.uses_extended_fx
        all_effects = Effects.get_all_effects()
        return {e.name for e in all_effects if Effects.supports_protocol(e.name, uses_extended)}

    @property
    def uses_extended_fx(self) -> bool:
        """
        True if device uses extended FX commands (class 0x0F).

        :return: True if extended FX commands are used
        """
        return self.device.hardware.uses_extended_fx

    # ─────────────────────────────────────────────────────────────────────────
    # Connectivity Capabilities
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def is_wireless(self) -> bool:
        """
        True if device has wireless/battery capabilities.

        :return: True if device is wireless
        """
        return self.device.hardware.has_capability(Capability.WIRELESS)

    @property
    def supports_hyperpolling(self) -> bool:
        """
        True if device supports HyperPolling (>1000Hz).

        :return: True if HyperPolling is supported
        """
        return self.device.hardware.has_capability(Capability.HYPERPOLLING)

    # ─────────────────────────────────────────────────────────────────────────
    # Input Capabilities
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def has_analog_keys(self) -> bool:
        """
        True if device supports analog key actuation.

        :return: True if analog keys are supported
        """
        return self.device.hardware.has_capability(Capability.ANALOG_KEYS)

    @property
    def has_profile_leds(self) -> bool:
        """
        True if device has individual profile indicator LEDs.

        :return: True if profile LEDs are present
        """
        return self.device.hardware.has_capability(Capability.PROFILE_LEDS)

    # ─────────────────────────────────────────────────────────────────────────
    # Protocol Capabilities
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def protocol_version(self) -> str:
        """
        Get the protocol version name for this device.

        :return: Protocol version string (e.g., 'legacy', 'extended', 'modern')
        """
        config = self.device.hardware.get_protocol_config()
        return config.version.value

    @property
    def transaction_id(self) -> int:
        """
        Get the transaction ID used for this device.

        :return: Transaction ID byte value
        """
        config = self.device.hardware.get_protocol_config()
        return config.transaction_id

    # ─────────────────────────────────────────────────────────────────────────
    # Comprehensive Info
    # ─────────────────────────────────────────────────────────────────────────

    def get_all_capabilities(self) -> dict[str, bool | str | set[str] | tuple[int, int] | None]:
        """
        Get comprehensive capability information.

        :return: Dictionary with all capability flags and info
        """
        return {
            # LEDs
            "has_leds": self.has_leds,
            "has_matrix": self.has_matrix,
            "is_single_led": self.is_single_led,
            "matrix_dimensions": self.matrix_dimensions,
            # Effects
            "uses_extended_fx": self.uses_extended_fx,
            "requires_software_effects": self.requires_software_effects,
            "supported_effects": self.supported_effects,
            # Connectivity
            "is_wireless": self.is_wireless,
            "supports_hyperpolling": self.supports_hyperpolling,
            # Input
            "has_analog_keys": self.has_analog_keys,
            "has_profile_leds": self.has_profile_leds,
            # Protocol
            "protocol_version": self.protocol_version,
            "transaction_id": self.transaction_id,
        }


def get_device_capabilities(device: BaseUChromaDevice) -> DeviceCapabilities:
    """
    Create a DeviceCapabilities instance for a device.

    :param device: The device to query capabilities for
    :return: DeviceCapabilities instance
    """
    return DeviceCapabilities(device)
