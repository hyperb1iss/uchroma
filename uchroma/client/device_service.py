#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Device service layer for CLI commands.

Bridges device matching, D-Bus client, and commands.
Handles connection errors gracefully.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from uchroma.client.device_matcher import DeviceMatcher, parse_device_spec

if TYPE_CHECKING:
    from uchroma.client.dbus_client import DeviceProxy


@dataclass
class DeviceInfo:
    """Lightweight device info for listing (no D-Bus proxy needed)."""

    name: str
    device_type: str
    key: str
    index: int
    serial: str = ""
    firmware: str = ""
    brightness: int = 0


class DeviceService:
    """
    Service layer for device operations.

    Provides:
    - Device listing with graceful fallback
    - Fuzzy device selection via DeviceMatcher
    - Connection state management
    """

    def __init__(self):
        self._client = None
        self._connected = False
        self._connection_error: str | None = None

    def _ensure_client(self):
        """Lazily create client on first use."""
        if self._client is None:
            try:
                # Lazy import: dbus_client may not be available in all environments
                from uchroma.client.dbus_client import UChromaClient  # noqa: PLC0415

                self._client = UChromaClient()
            except ImportError as e:
                self._connection_error = f"D-Bus client unavailable: {e}"
                return False
        return True

    def _try_connect(self) -> bool:
        """Try to connect to daemon, return success."""
        if self._connected:
            return True

        if not self._ensure_client():
            return False

        try:
            # Connection happens lazily on first call
            self._client.get_device_paths()
            self._connected = True
            return True
        except Exception as e:
            self._connection_error = f"Cannot connect to uchromad: {e}"
            return False

    @property
    def is_connected(self) -> bool:
        """Check if connected to daemon."""
        return self._connected

    @property
    def connection_error(self) -> str | None:
        """Get connection error message if any."""
        return self._connection_error

    # ─────────────────────────────────────────────────────────────────────────
    # Device Listing
    # ─────────────────────────────────────────────────────────────────────────

    def list_devices(self) -> list[DeviceInfo]:
        """
        List all connected devices.

        Returns empty list if daemon not running.
        """
        if not self._try_connect():
            return []

        devices = []
        try:
            for path in self._client.get_device_paths():
                proxy = self._client.get_device(path)
                if proxy:
                    devices.append(
                        DeviceInfo(
                            name=proxy.Name,
                            device_type=proxy.DeviceType,
                            key=proxy.Key,
                            index=proxy.DeviceIndex,
                            serial=proxy.SerialNumber or "",
                            firmware=proxy.FirmwareVersion or "",
                            brightness=int(proxy.Brightness),
                        )
                    )
        except Exception:
            pass

        return devices

    def _build_matcher_devices(self) -> list[dict]:
        """Build device list in format expected by DeviceMatcher."""
        devices = []
        for info in self.list_devices():
            devices.append(
                {
                    "name": info.name,
                    "type": info.device_type,
                    "key": info.key,
                    "index": info.index,
                    "path": f"/io/uchroma/{info.key.replace(':', '_').replace('.', '_')}",
                }
            )
        return devices

    # ─────────────────────────────────────────────────────────────────────────
    # Device Selection
    # ─────────────────────────────────────────────────────────────────────────

    def get_device(self, spec: str | None) -> "DeviceProxy | None":
        """
        Get device by spec string (fuzzy match, index, key, or path).

        Args:
            spec: Device specifier or None for auto-select

        Returns:
            DeviceProxy or None

        Raises:
            ValueError: If spec is ambiguous or no match
        """
        if not self._try_connect():
            return None

        devices = self._build_matcher_devices()
        if not devices:
            return None

        matcher = DeviceMatcher(devices)

        if spec is None:
            # Auto-select if single device
            match = matcher.auto_select()
        else:
            match_type, value = parse_device_spec(spec)
            if match_type == "path":
                return self._client.get_device(value)
            match = matcher.match(match_type, value)

        if match is None:
            return None

        # Get the actual proxy
        return self._client.get_device(match["key"])

    def require_device(self, spec: str | None) -> "DeviceProxy":
        """
        Get device, raising error if not found.

        Args:
            spec: Device specifier

        Returns:
            DeviceProxy

        Raises:
            ValueError: If device not found or ambiguous
        """
        if not self._try_connect():
            raise ValueError(self._connection_error or "Cannot connect to daemon")

        devices = self._build_matcher_devices()
        if not devices:
            raise ValueError("No devices found")

        matcher = DeviceMatcher(devices)

        if spec is None:
            match = matcher.auto_select()  # Raises if ambiguous
        else:
            match_type, value = parse_device_spec(spec)
            if match_type == "path":
                proxy = self._client.get_device(value)
                if proxy is None:
                    raise ValueError(f"Device not found: {spec}")
                return proxy
            match = matcher.match(match_type, value)  # Raises if not found

        proxy = self._client.get_device(match["key"])
        if proxy is None:
            raise ValueError(f"Device not found: {spec}")

        return proxy

    # ─────────────────────────────────────────────────────────────────────────
    # Device Operations
    # ─────────────────────────────────────────────────────────────────────────

    def get_brightness(self, device: "DeviceProxy", led: str | None = None) -> int:
        """Get brightness as percentage (0-100)."""
        # TODO: Handle per-LED brightness
        # Device returns 0-100 directly
        return int(device.Brightness)

    def set_brightness(self, device: "DeviceProxy", value: int, led: str | None = None) -> bool:
        """Set brightness from percentage (0-100)."""
        if not 0 <= value <= 100:
            raise ValueError(f"Brightness must be 0-100, got {value}")

        # TODO: Handle per-LED brightness
        # Device expects 0-100 directly
        device.Brightness = float(value)
        return True

    def set_effect(
        self,
        device: "DeviceProxy",
        effect: str,
        color: str | None = None,
        color2: str | None = None,
        speed: int = 2,
        direction: str = "right",
    ) -> bool:
        """Apply hardware effect."""
        if device._fx_iface is None:
            raise ValueError("Device does not support hardware effects")

        # Build args dict based on effect
        args = {}
        if color:
            args["color"] = color
        if color2:
            args["color2"] = color2
        if effect == "wave":
            args["direction"] = direction
        if effect in ("reactive", "starlight"):
            args["speed"] = speed

        return device.SetFX(effect, args)

    def set_fx(self, device: "DeviceProxy", fx_name: str, fx_args: dict | None = None) -> bool:
        """Apply hardware effect with arbitrary arguments."""
        from uchroma.dbus_utils import dbus_prepare  # noqa: PLC0415

        prepared, _ = dbus_prepare(fx_args or {}, variant=True)
        return device.SetFX(fx_name, prepared)

    # ─────────────────────────────────────────────────────────────────────────
    # Animation Operations
    # ─────────────────────────────────────────────────────────────────────────

    def get_available_renderers(self, device: "DeviceProxy") -> dict | None:
        """Get available animation renderers with metadata and traits."""
        return device.AvailableRenderers

    def get_current_renderers(self, device: "DeviceProxy") -> list | None:
        """Get currently active renderer layers."""
        return device.CurrentRenderers

    def get_active_layers(self, device: "DeviceProxy") -> list[dict] | None:
        """Get info about active animation layers for profile saving."""
        renderers = self.get_current_renderers(device)
        if not renderers:
            return None

        def unwrap_variants(obj):
            try:
                from dbus_fast import Variant  # noqa: PLC0415
            except ImportError:
                Variant = None  # type: ignore[assignment]

            if Variant is not None and isinstance(obj, Variant):
                return unwrap_variants(obj.value)
            if isinstance(obj, dict):
                return {k: unwrap_variants(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [unwrap_variants(v) for v in obj]
            if isinstance(obj, tuple):
                return tuple(unwrap_variants(v) for v in obj)
            return obj

        def parse_zindex(path: str, fallback: int) -> int:
            try:
                return int(path.rsplit("/", 1)[-1])
            except (ValueError, AttributeError):
                return fallback

        layers = []
        for i, entry in enumerate(renderers):
            if isinstance(entry, (list, tuple)) and len(entry) == 2:
                renderer_name, layer_path = entry
                zindex = parse_zindex(str(layer_path), i)
            else:
                renderer_name = entry
                zindex = i

            layer_info = self.get_layer_info(device, zindex)
            unwrapped = unwrap_variants(layer_info or {})
            args = {}
            if isinstance(unwrapped.get("traits"), dict):
                args = unwrapped["traits"]
            else:
                args = {
                    k: v
                    for k, v in unwrapped.items()
                    if not k.startswith("_") and k not in {"Key", "ZIndex", "Type"}
                }
            layers.append(
                {
                    "renderer": renderer_name,
                    "zindex": zindex,
                    "args": args,
                }
            )
        return layers

    def add_renderer(
        self, device: "DeviceProxy", name: str, zindex: int = -1, traits: dict | None = None
    ) -> str | None:
        """
        Add an animation renderer layer.

        Args:
            device: Device proxy
            name: Fully qualified renderer name (e.g., 'uchroma.fxlib.plasma.Plasma')
            zindex: Layer index (-1 for auto)
            traits: Optional trait overrides

        Returns:
            Layer path on success, None on failure
        """
        # Convert traits to D-Bus variants
        from uchroma.dbus_utils import dbus_prepare  # noqa: PLC0415

        prepared, _ = dbus_prepare(traits or {}, variant=True)
        return device.AddRenderer(name, zindex, prepared)

    def remove_renderer(self, device: "DeviceProxy", zindex: int) -> bool:
        """Remove a renderer layer by index."""
        return device.RemoveRenderer(zindex)

    def pause_animation(self, device: "DeviceProxy") -> bool:
        """Toggle animation pause state. Returns new pause state."""
        return device.PauseAnimation()

    def stop_animation(self, device: "DeviceProxy") -> bool:
        """Stop and clear all animation layers."""
        return device.StopAnimation()

    def get_layer_info(self, device: "DeviceProxy", zindex: int) -> dict | None:
        """Get properties for a specific layer."""
        if not self._try_connect():
            return None
        return self._client.get_layer_info(device, zindex)

    def set_layer_traits(self, device: "DeviceProxy", zindex: int, traits: dict) -> bool:
        """Set traits on a running layer."""
        from uchroma.dbus_utils import dbus_prepare  # noqa: PLC0415

        prepared, _ = dbus_prepare(traits, variant=True)
        return device.SetLayerTraits(zindex, prepared)

    # ─────────────────────────────────────────────────────────────────────────
    # LED Operations
    # ─────────────────────────────────────────────────────────────────────────

    def get_available_leds(self, device: "DeviceProxy") -> dict | None:
        """Get available LEDs with their traits."""
        return device.AvailableLEDs

    def get_led_state(self, device: "DeviceProxy", led_name: str) -> dict | None:
        """Get current state of an LED."""
        return device.GetLED(led_name)

    def set_led(self, device: "DeviceProxy", led_name: str, props: dict) -> bool:
        """Set LED properties."""
        from uchroma.dbus_utils import dbus_prepare  # noqa: PLC0415

        prepared, _ = dbus_prepare(props, variant=True)
        return device.SetLED(led_name, prepared)

    # ─────────────────────────────────────────────────────────────────────────
    # System Control Operations (laptops)
    # ─────────────────────────────────────────────────────────────────────────

    def has_system_control(self, device: "DeviceProxy") -> bool:
        """Check if device supports system control (fans, power modes, boost)."""
        return device.HasSystemControl

    def get_fan_rpm(self, device: "DeviceProxy") -> tuple[int, int] | None:
        """Get current fan RPM values."""
        return device.FanRPM

    def get_fan_mode(self, device: "DeviceProxy") -> str | None:
        """Get current fan mode (auto/manual)."""
        return device.FanMode

    def get_fan_limits(self, device: "DeviceProxy") -> dict | None:
        """Get fan RPM limits (min/max values)."""
        return device.FanLimits

    def set_fan_auto(self, device: "DeviceProxy") -> bool:
        """Set fans to automatic control."""
        return device.SetFanAuto()

    def set_fan_rpm(self, device: "DeviceProxy", rpm: int, fan2_rpm: int = -1) -> bool:
        """Set manual fan RPM. Use -1 for fan2_rpm to copy rpm value."""
        return device.SetFanRPM(rpm, fan2_rpm)

    def get_power_mode(self, device: "DeviceProxy") -> str | None:
        """Get current power mode."""
        return device.PowerMode

    def set_power_mode(self, device: "DeviceProxy", mode: str) -> bool:
        """Set power mode (balanced, gaming, creator, custom)."""
        device.PowerMode = mode
        return True

    def get_available_power_modes(self, device: "DeviceProxy") -> list[str] | None:
        """Get available power modes."""
        return device.AvailablePowerModes

    def get_cpu_boost(self, device: "DeviceProxy") -> str | None:
        """Get current CPU boost mode."""
        return device.CPUBoost

    def set_cpu_boost(self, device: "DeviceProxy", mode: str) -> bool:
        """Set CPU boost mode."""
        device.CPUBoost = mode
        return True

    def get_gpu_boost(self, device: "DeviceProxy") -> str | None:
        """Get current GPU boost mode."""
        return device.GPUBoost

    def set_gpu_boost(self, device: "DeviceProxy", mode: str) -> bool:
        """Set GPU boost mode."""
        device.GPUBoost = mode
        return True

    def get_available_boost_modes(self, device: "DeviceProxy") -> list[str] | None:
        """Get available boost modes."""
        return device.AvailableBoostModes

    def supports_fan_speed(self, device: "DeviceProxy") -> bool:
        """Check if device supports reading fan speed."""
        return device.SupportsFanSpeed

    def supports_boost(self, device: "DeviceProxy") -> bool:
        """Check if device supports boost control."""
        return device.SupportsBoost

    # ─────────────────────────────────────────────────────────────────────────
    # Battery/Wireless Operations
    # ─────────────────────────────────────────────────────────────────────────

    def is_wireless(self, device: "DeviceProxy") -> bool:
        """Check if device is wireless."""
        return device.IsWireless

    def is_charging(self, device: "DeviceProxy") -> bool:
        """Check if device is charging."""
        return device.IsCharging

    def get_battery_level(self, device: "DeviceProxy") -> int:
        """Get battery level as percentage (0-100)."""
        return device.BatteryLevel


# Singleton for CLI use
_service: DeviceService | None = None


def get_device_service() -> DeviceService:
    """Get the singleton device service instance."""
    global _service
    if _service is None:
        _service = DeviceService()
    return _service
