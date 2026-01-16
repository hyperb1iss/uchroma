#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
System control for Razer Blade laptops - fan control, power modes, and boost.

Protocol reference:
- razer-laptop-control: https://github.com/rnd-ash/razer-laptop-control
- OpenRazer PR #1227: https://github.com/openrazer/openrazer/pull/1227
"""

from dataclasses import dataclass
from enum import IntEnum

from uchroma.util import Signal

from .hardware import Capability, Hardware
from .types import BaseCommand


class PowerMode(IntEnum):
    """Laptop power profiles."""

    BALANCED = 0  # ~35W CPU TDP, quiet fans
    GAMING = 1  # ~55W CPU TDP, aggressive cooling
    CREATOR = 2  # Higher GPU TDP, select models only
    CUSTOM = 4  # Manual fan/boost control active


class BoostMode(IntEnum):
    """CPU/GPU boost settings (used with CUSTOM power mode)."""

    LOW = 0
    MEDIUM = 1
    HIGH = 2
    BOOST = 3  # Maximum performance


class FanMode(IntEnum):
    """Fan control modes."""

    AUTO = 0  # EC controls fan speed
    MANUAL = 1  # User-specified RPM


@dataclass
class FanLimits:
    """Fan RPM limits for a specific laptop model."""

    min_rpm: int = 0  # 0 = automatic
    min_manual_rpm: int = 3500  # Minimum safe manual RPM
    max_rpm: int = 5000  # Maximum RPM
    supports_dual_fan: bool = False  # Has separate CPU/GPU fans


# Model-specific fan limits (based on community research)
FAN_LIMITS = {
    "Blade 15": FanLimits(max_rpm=5000, supports_dual_fan=True),
    "Blade 17": FanLimits(max_rpm=5300, supports_dual_fan=True),
    "Blade 14": FanLimits(max_rpm=5000, supports_dual_fan=False),
    "Blade Stealth": FanLimits(max_rpm=4500, supports_dual_fan=False),
    "default": FanLimits(max_rpm=5000, supports_dual_fan=False),
}


class ECCommand(BaseCommand):
    """Embedded Controller commands for Blade laptops (Class 0x0D).

    Per OpenRazer PR #1227, SET_FAN_MODE is a combined command that sets
    both power mode (game_mode) and fan RPM in a single call.

    Command structure for SET_FAN_MODE (0x0D, 0x02):
        args[0]: 0x00 (reserved)
        args[1]: fan_id (0x00 or 0x01 for dual-fan)
        args[2]: game_mode (power profile: 0=balanced, 1=gaming, 2=creator, 4=custom)
        args[3]: fan_speed (RPM/100, or 0 for auto)

    Command structure for GET_FAN_MODE (0x0D, 0x82):
        Returns: args[2]=game_mode, args[3]=fan_mode

    Command structure for GET_FAN_SPEED (0x0D, 0x81):
        args[0]: 0x00 (reserved)
        args[1]: fan_id
        Returns: args[2]=speed (RPM/100)
    """

    # Combined fan/power control
    SET_FAN_MODE = (0x0D, 0x02, 0x04)  # Set fan mode AND power mode
    GET_FAN_MODE = (0x0D, 0x82, 0x04)  # Query fan mode AND power mode
    GET_FAN_SPEED = (0x0D, 0x81, 0x03)  # Query actual fan RPM

    # CPU/GPU boost (for CUSTOM mode) - may not be supported on all models
    SET_BOOST = (0x0D, 0x0D, None)  # Set boost levels
    GET_BOOST = (0x0D, 0x8D, None)  # Query boost state


class SystemControlMixin:
    """
    Mixin for laptop system control (fan, power modes, boost).

    Add this to UChromaLaptop to enable EC control features.
    Requires the host class to have:
    - hardware: Hardware
    - run_command(*args) -> bool
    - run_with_result(*args) -> bytes | None
    - logger
    """

    # Type hints for mixin methods (implemented by host class)
    hardware: "Hardware"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Signals for state change notifications
        self.fan_changed = Signal()
        self.power_mode_changed = Signal()

        # Cache for current state
        self._cached_power_mode: PowerMode | None = None
        self._cached_fan_mode: FanMode = FanMode.AUTO

    @property
    def supports_system_control(self) -> bool:
        """Check if device supports EC control (basic fan/power modes)."""
        return self.hardware.has_capability(Capability.EC_FAN_CONTROL)

    @property
    def supports_fan_speed(self) -> bool:
        """Check if device supports real-time fan RPM reading."""
        return self.hardware.has_capability(Capability.EC_FAN_SPEED)

    @property
    def supports_boost(self) -> bool:
        """Check if device supports CPU/GPU boost control."""
        return self.hardware.has_capability(Capability.EC_BOOST)

    @property
    def fan_limits(self) -> FanLimits:
        """Get fan limits for this laptop model."""
        if not hasattr(self, "hardware") or not self.hardware.name:
            return FAN_LIMITS["default"]

        for model_prefix, limits in FAN_LIMITS.items():
            if model_prefix != "default" and model_prefix in self.hardware.name:
                return limits
        return FAN_LIMITS["default"]

    # ─────────────────────────────────────────────────────────────────────────
    # Fan Control
    # ─────────────────────────────────────────────────────────────────────────

    def _get_fan_state(self) -> tuple[PowerMode, int, int | None]:
        """
        Get combined fan/power state from GET_FAN_MODE.

        Returns:
            Tuple of (power_mode, fan1_rpm, fan2_rpm)
        """
        result = self.run_with_result(ECCommand.GET_FAN_MODE, 0x00, 0x00, 0x00, 0x00)
        if result is None or len(result) < 4:
            return (PowerMode.BALANCED, 0, None)

        # args[2] = game_mode (power profile)
        # args[3] = fan_speed (RPM/100, 0 = auto)
        try:
            power_mode = PowerMode(result[2])
        except ValueError:
            power_mode = PowerMode.BALANCED

        fan1_rpm = result[3] * 100

        # Query fan 2 if dual-fan
        fan2_rpm = None
        if self.fan_limits.supports_dual_fan:
            result2 = self.run_with_result(ECCommand.GET_FAN_MODE, 0x00, 0x01, 0x00, 0x00)
            if result2 is not None and len(result2) >= 4:
                fan2_rpm = result2[3] * 100

        return (power_mode, fan1_rpm, fan2_rpm)

    @property
    def fan_rpm(self) -> tuple[int, int | None]:
        """
        Get current fan RPM.

        If device supports EC_FAN_SPEED, uses GET_FAN_SPEED for actual RPM.
        Otherwise falls back to GET_FAN_MODE (configured speed setting).

        Returns:
            Tuple of (fan1_rpm, fan2_rpm) - fan2 is None if single fan
        """
        if not self.supports_system_control:
            return (0, None)

        # Only try GET_FAN_SPEED if device supports it
        if self.supports_fan_speed:
            result = self.run_with_result(ECCommand.GET_FAN_SPEED, 0x00, 0x00)
            if result is not None and len(result) >= 3:
                fan1 = result[2] * 100
                fan2 = None
                if self.fan_limits.supports_dual_fan:
                    result2 = self.run_with_result(ECCommand.GET_FAN_SPEED, 0x00, 0x01)
                    if result2 is not None and len(result2) >= 3:
                        fan2 = result2[2] * 100
                return (fan1, fan2)

        # Fall back to GET_FAN_MODE for configured speed (not actual RPM)
        result = self.run_with_result(ECCommand.GET_FAN_MODE, 0x00, 0x00, 0x00, 0x00)
        if result is None or len(result) < 4:
            return (0, None)

        # args[3] = fan_speed setting (RPM/100, 0 = auto)
        fan1 = result[3] * 100

        fan2 = None
        if self.fan_limits.supports_dual_fan:
            result2 = self.run_with_result(ECCommand.GET_FAN_MODE, 0x00, 0x01, 0x00, 0x00)
            if result2 is not None and len(result2) >= 4:
                fan2 = result2[3] * 100

        return (fan1, fan2)

    @property
    def fan_mode(self) -> FanMode:
        """Get current fan mode (auto or manual) from GET_FAN_MODE."""
        if not self.supports_system_control:
            return FanMode.AUTO

        result = self.run_with_result(ECCommand.GET_FAN_MODE, 0x00, 0x00, 0x00, 0x00)
        if result is None or len(result) < 4:
            return self._cached_fan_mode

        # args[3] = fan_speed: 0 = auto, >0 = manual
        self._cached_fan_mode = FanMode.MANUAL if result[3] > 0 else FanMode.AUTO
        return self._cached_fan_mode

    def _set_fan_power(self, power_mode: PowerMode, fan_rpm: int, fan_id: int = 0) -> bool:
        """
        Set combined fan/power state using SET_FAN_MODE.

        Args:
            power_mode: Power profile to set
            fan_rpm: Fan RPM (0 = auto)
            fan_id: Fan index (0 or 1 for dual-fan)

        Returns:
            True if successful
        """
        # Convert RPM to protocol value (RPM / 100)
        rpm_value = fan_rpm // 100 if fan_rpm > 0 else 0

        # SET_FAN_MODE: [reserved, fan_id, game_mode, fan_speed]
        return self.run_command(ECCommand.SET_FAN_MODE, 0x00, fan_id, power_mode.value, rpm_value)

    def set_fan_auto(self) -> bool:
        """Set fans to automatic EC control (keeps current power mode)."""
        if not self.supports_system_control:
            return False

        # Get current power mode to preserve it
        current_power = self._cached_power_mode or self.power_mode

        # Set fan to auto (rpm=0) while keeping power mode
        success = self._set_fan_power(current_power, 0, 0)

        if success and self.fan_limits.supports_dual_fan:
            self._set_fan_power(current_power, 0, 1)

        if success:
            self._cached_fan_mode = FanMode.AUTO
            self.fan_changed.fire(self)
        return success

    def set_fan_rpm(self, rpm: int, fan2_rpm: int | None = None) -> bool:
        """
        Set manual fan RPM.

        Args:
            rpm: Target RPM for fan 1 (0 = auto)
            fan2_rpm: Optional separate RPM for fan 2 (dual-fan models only)

        Returns:
            True if successful

        Raises:
            ValueError: If RPM is outside safe limits
        """
        if not self.supports_system_control:
            return False

        limits = self.fan_limits

        # RPM 0 means auto mode
        if rpm == 0:
            return self.set_fan_auto()

        # Validate RPM limits
        if rpm < limits.min_manual_rpm:
            raise ValueError(
                f"RPM {rpm} below minimum {limits.min_manual_rpm}. "
                f"Use set_fan_auto() for automatic control."
            )
        if rpm > limits.max_rpm:
            raise ValueError(f"RPM {rpm} exceeds maximum {limits.max_rpm}")

        # Get current power mode to preserve it (or use CUSTOM for manual fan)
        current_power = self._cached_power_mode or PowerMode.CUSTOM

        # Set fan 1
        success = self._set_fan_power(current_power, rpm, 0)

        # Set fan 2 if dual-fan and specified
        if success and fan2_rpm is not None and limits.supports_dual_fan:
            if fan2_rpm < limits.min_manual_rpm or fan2_rpm > limits.max_rpm:
                raise ValueError(f"Fan 2 RPM {fan2_rpm} outside limits")
            success = self._set_fan_power(current_power, fan2_rpm, 1)

        if success:
            self._cached_fan_mode = FanMode.MANUAL
            self.fan_changed.fire(self)

        return success

    # ─────────────────────────────────────────────────────────────────────────
    # Power Modes
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def power_mode(self) -> PowerMode:
        """Get current power mode from GET_FAN_MODE."""
        if not self.supports_system_control:
            return PowerMode.BALANCED

        result = self.run_with_result(ECCommand.GET_FAN_MODE, 0x00, 0x00, 0x00, 0x00)
        if result is None or len(result) < 3:
            return self._cached_power_mode or PowerMode.BALANCED

        try:
            mode = PowerMode(result[2])
            self._cached_power_mode = mode
            return mode
        except ValueError:
            return PowerMode.BALANCED

    @power_mode.setter
    def power_mode(self, mode: PowerMode):
        """Set power mode (preserves current fan setting)."""
        if not self.supports_system_control:
            return

        # Get current fan RPM to preserve it (or 0 for auto)
        current_fan_rpm = 0
        result = self.run_with_result(ECCommand.GET_FAN_MODE, 0x00, 0x00, 0x00, 0x00)
        if result is not None and len(result) >= 4:
            current_fan_rpm = result[3] * 100

        # Set new power mode with current fan setting
        success = self._set_fan_power(mode, current_fan_rpm, 0)

        if success and self.fan_limits.supports_dual_fan:
            # Also set fan 2 with same power mode
            result2 = self.run_with_result(ECCommand.GET_FAN_MODE, 0x00, 0x01, 0x00, 0x00)
            fan2_rpm = result2[3] * 100 if result2 and len(result2) >= 4 else 0
            self._set_fan_power(mode, fan2_rpm, 1)

        if success:
            self._cached_power_mode = mode
            self.power_mode_changed.fire(self, mode)

    def set_gaming_mode(self) -> bool:
        """Enable gaming mode (~55W CPU TDP, aggressive cooling)."""
        self.power_mode = PowerMode.GAMING
        return True

    def set_balanced_mode(self) -> bool:
        """Enable balanced mode (~35W CPU TDP, quiet operation)."""
        self.power_mode = PowerMode.BALANCED
        return True

    def set_creator_mode(self) -> bool:
        """Enable creator mode (higher GPU TDP)."""
        self.power_mode = PowerMode.CREATOR
        return True

    def set_custom_mode(self) -> bool:
        """Enable custom mode (manual fan/boost control)."""
        self.power_mode = PowerMode.CUSTOM
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Boost Control (for CUSTOM power mode)
    # Only available on select models (Blade 15 Advanced 2020, Studio 2020)
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def cpu_boost(self) -> BoostMode:
        """Get CPU boost mode."""
        if not self.supports_boost:
            return BoostMode.LOW

        result = self.run_with_result(ECCommand.GET_BOOST, 0x01, 0x00)
        if result is None or len(result) < 1:
            return BoostMode.LOW

        try:
            return BoostMode(result[0])
        except ValueError:
            return BoostMode.LOW

    @cpu_boost.setter
    def cpu_boost(self, mode: BoostMode):
        """Set CPU boost mode (requires CUSTOM power mode)."""
        if not self.supports_boost:
            return
        self.run_command(ECCommand.SET_BOOST, 0x01, 0x00, mode.value)

    @property
    def gpu_boost(self) -> BoostMode:
        """Get GPU boost mode."""
        if not self.supports_boost:
            return BoostMode.LOW

        result = self.run_with_result(ECCommand.GET_BOOST, 0x01, 0x01)
        if result is None or len(result) < 1:
            return BoostMode.LOW

        try:
            return BoostMode(result[0])
        except ValueError:
            return BoostMode.LOW

    @gpu_boost.setter
    def gpu_boost(self, mode: BoostMode):
        """Set GPU boost mode (requires CUSTOM power mode)."""
        if not self.supports_boost:
            return
        self.run_command(ECCommand.SET_BOOST, 0x01, 0x01, mode.value)
