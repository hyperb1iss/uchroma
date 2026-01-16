#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#

# pylint: disable=invalid-name,protected-access

"""
D-Bus interfaces using dbus-fast (pure asyncio)

These interfaces are designed to exist as a separate layer
and do not contain recursive dependencies with the lower
layers. UI clients should be designed to use these interfaces
rather than interacting with the hardware directly.
"""

import asyncio
import os
from collections import OrderedDict
from enum import Enum

import numpy as np
from dbus_fast import BusType, PropertyAccess, Variant
from dbus_fast.aio import MessageBus
from dbus_fast.service import ServiceInterface, dbus_property, method, signal

from uchroma.dbus_utils import dbus_prepare
from uchroma.util import Signal

from .system_control import BoostMode, PowerMode
from .types import LEDType


def dev_mode_enabled():
    return os.environ.get("UCHROMA_DEV") is not None


BUS_NAME = "io.uchroma"
ROOT_PATH = "/io/uchroma"


def _interface_properties(iface: ServiceInterface) -> dict:
    props = {}
    logger = getattr(iface, "_logger", None)
    for prop in ServiceInterface._get_properties(iface):
        if getattr(prop, "disabled", False):
            continue
        try:
            value = prop.prop_getter(iface)
        except Exception as exc:
            if logger is not None:
                logger.warning(
                    "ObjectManager skipped %s.%s: %s",
                    iface.name,
                    prop.name,
                    exc,
                )
            continue
        props[prop.name] = Variant(prop.signature, value)
    return props


class DeviceInterface(ServiceInterface):
    """
    D-Bus interface for device properties and common hardware features.
    """

    def __init__(self, driver, device_api):
        super().__init__("io.uchroma.Device")
        self._driver = driver
        self._device_api = device_api
        self._logger = driver.logger
        self._signal_input = False
        self._input_task = None
        self._input_queue = None

    # Read-only properties
    @dbus_property(access=PropertyAccess.READ)
    def Name(self) -> "s":
        return self._driver.name or ""

    @dbus_property(access=PropertyAccess.READ)
    def DeviceType(self) -> "s":
        dt = self._driver.device_type
        return dt.name.lower() if isinstance(dt, Enum) else str(dt)

    @dbus_property(access=PropertyAccess.READ)
    def DriverVersion(self) -> "s":
        return getattr(self._driver, "driver_version", "") or ""

    @dbus_property(access=PropertyAccess.READ)
    def FirmwareVersion(self) -> "s":
        return getattr(self._driver, "firmware_version", "") or ""

    @dbus_property(access=PropertyAccess.READ)
    def SerialNumber(self) -> "s":
        return getattr(self._driver, "serial_number", "") or ""

    @dbus_property(access=PropertyAccess.READ)
    def Manufacturer(self) -> "s":
        return getattr(self._driver, "manufacturer", "") or ""

    @dbus_property(access=PropertyAccess.READ)
    def VendorId(self) -> "u":
        return self._driver.vendor_id or 0

    @dbus_property(access=PropertyAccess.READ)
    def ProductId(self) -> "u":
        return self._driver.product_id or 0

    @dbus_property(access=PropertyAccess.READ)
    def DeviceIndex(self) -> "u":
        return getattr(self._driver, "device_index", 0) or 0

    @dbus_property(access=PropertyAccess.READ)
    def HasMatrix(self) -> "b":
        return getattr(self._driver, "has_matrix", False)

    @dbus_property(access=PropertyAccess.READ)
    def Width(self) -> "i":
        return getattr(self._driver, "width", 0) or 0

    @dbus_property(access=PropertyAccess.READ)
    def Height(self) -> "i":
        return getattr(self._driver, "height", 0) or 0

    @dbus_property(access=PropertyAccess.READ)
    def SysPath(self) -> "s":
        return getattr(self._driver, "sys_path", "") or ""

    @dbus_property(access=PropertyAccess.READ)
    def Key(self) -> "s":
        return getattr(self._driver, "key", "") or ""

    @dbus_property(access=PropertyAccess.READ)
    def BusPath(self) -> "o":
        return self._device_api.bus_path

    @dbus_property(access=PropertyAccess.READ)
    def IsWireless(self) -> "b":
        return getattr(self._driver, "is_wireless", False)

    @dbus_property(access=PropertyAccess.READ)
    def IsCharging(self) -> "b":
        return getattr(self._driver, "is_charging", False)

    @dbus_property(access=PropertyAccess.READ)
    def BatteryLevel(self) -> "d":
        return getattr(self._driver, "battery_level", 0.0) or 0.0

    @dbus_property(access=PropertyAccess.READ)
    def SupportedLeds(self) -> "as":
        leds = getattr(self._driver, "supported_leds", [])
        return [x.name.lower() for x in leds]

    @dbus_property(access=PropertyAccess.READ)
    def Zones(self) -> "as":
        zones = getattr(self._driver, "zones", [])
        if isinstance(zones, (list, tuple)):
            return [str(z) for z in zones]
        return []

    @dbus_property(access=PropertyAccess.READ)
    def KeyMapping(self) -> "a{sa(ii)}":
        mapping = OrderedDict()
        keymap = getattr(self._driver, "key_mapping", None)
        if not keymap:
            return mapping

        for key, points in keymap.items():
            if points is None:
                continue
            # Check if points is a single coordinate (2-tuple with int elements)
            # vs a collection of coordinates (PointList/list of Points)
            if len(points) == 2 and isinstance(points[0], int):
                # Single point like Point(0, 1)
                mapping[str(key)] = [tuple(points)]
            else:
                # Collection of points - convert each to tuple
                mapping[str(key)] = [tuple(p) for p in points]

        return mapping

    # Read-write properties
    @dbus_property()
    def Brightness(self) -> "d":
        return getattr(self._driver, "brightness", 0.0) or 0.0

    @Brightness.setter
    def Brightness(self, value: "d"):
        if value < 0.0 or value > 100.0:
            return
        old = self._driver.brightness
        self._driver.brightness = value
        if old != self._driver.brightness:
            self.emit_properties_changed({"Brightness": value})

    @dbus_property()
    def Suspended(self) -> "b":
        return getattr(self._driver, "suspended", False)

    @Suspended.setter
    def Suspended(self, value: "b"):
        current = getattr(self._driver, "suspended", False)
        if value == current:
            return
        if value:
            self._driver.suspend()
        else:
            self._driver.resume()
        if current != self._driver.suspended:
            self.emit_properties_changed({"Suspended": self._driver.suspended})

    @method()
    def Reset(self):
        self._driver.reset()


class LEDManagerInterface(ServiceInterface):
    """
    D-Bus interface for LED management.
    """

    def __init__(self, driver):
        super().__init__("io.uchroma.LEDManager")
        self._driver = driver
        self._logger = driver.logger
        self._driver.led_manager.led_changed.connect(self._led_changed)

    def _led_changed(self, led):
        self.LEDChanged(led.led_type.name.lower())

    @dbus_property(access=PropertyAccess.READ)
    def AvailableLEDs(self) -> "a{sa{sv}}":
        leds = {}
        for led in self._driver.led_manager.supported_leds:
            led_obj = self._driver.led_manager.get(led)
            traits = led_obj._trait_values if hasattr(led_obj, "_trait_values") else {}
            # Inner dict values need to be Variants for a{sv} signature
            leds[led.name.lower()] = dbus_prepare(traits, variant=True)[0]
        return leds

    @method()
    def GetLED(self, name: "s") -> "a{sv}":
        try:
            ledtype = LEDType[name.upper()]
        except KeyError:
            self._logger.error("Unknown LED type: %s", name)
            return {}
        led = self._driver.led_manager.get(ledtype)
        return dbus_prepare(led._trait_values, variant=True)[0]

    @method()
    def SetLED(self, name: "s", properties: "a{sv}") -> "b":
        try:
            ledtype = LEDType[name.upper()]
        except KeyError:
            self._logger.error("Unknown LED type: %s", name)
            return False

        led = self._driver.led_manager.get(ledtype)
        with led.hold_trait_notifications():
            self._logger.debug("Set LED property [%s]: %s", ledtype, properties)
            for k, v in properties.items():
                if led.has_trait(k):
                    # Extract value from Variant if needed
                    val = v.value if isinstance(v, Variant) else v
                    setattr(led, k, val)
        return True

    @signal()
    def LEDChanged(self, led: "s") -> "s":
        return led


class FXManagerInterface(ServiceInterface):
    """
    D-Bus interface for built-in effects.
    """

    def __init__(self, driver):
        super().__init__("io.uchroma.FXManager")
        self._driver = driver
        self._logger = driver.logger
        self._fx_manager = driver.fx_manager

        self._current_fx = None
        # Build FX metadata - each FX has a dict of trait_name -> full trait info
        self._available_fx = {}
        for fx_name, fx_class in self._fx_manager.available_fx.items():
            # Use trait_as_dict to serialize class traits without instantiating
            from uchroma.traits import trait_as_dict  # noqa: PLC0415

            fx_traits = {}
            for trait_name, trait in fx_class.class_traits().items():
                trait_dict = trait_as_dict(trait)
                if trait_dict:
                    obj, _sig = dbus_prepare(trait_dict, variant=True)
                    fx_traits[trait_name] = Variant("a{sv}", obj)
            self._available_fx[fx_name] = fx_traits

        self._fx_manager.observe(self._fx_changed, names=["current_fx"])

    def _fx_changed(self, change):
        self._logger.info("Effects changed: %s", change)
        self._current_fx = (
            change.new[0].lower(),
            dbus_prepare(change.new[1]._trait_values, variant=True)[0],
        )
        self.emit_properties_changed({"CurrentFX": self.CurrentFX})

    @dbus_property(access=PropertyAccess.READ)
    def AvailableFX(self) -> "a{sa{sv}}":
        return self._available_fx

    @dbus_property(access=PropertyAccess.READ)
    def CurrentFX(self) -> "(sa{sv})":
        if self._current_fx is None:
            return ("disable", {})
        return self._current_fx

    @method()
    def SetFX(self, name: "s", args: "a{sv}") -> "b":
        # Extract values from variants
        kwargs = {k: (v.value if isinstance(v, Variant) else v) for k, v in args.items()}
        return self._fx_manager.activate(name, **kwargs)


class AnimationManagerInterface(ServiceInterface):
    """
    D-Bus interface for animation/renderer management.
    """

    def __init__(self, driver, device_api):
        super().__init__("io.uchroma.AnimationManager")
        self._driver = driver
        self._device_api = device_api
        self._logger = driver.logger
        self._animgr = driver.animation_manager
        self._layers = []
        self._state = None

        self._animgr.layers_changed.connect(self._layers_changed)
        self._animgr.state_changed.connect(self._state_changed)

    def _sync_layers(self):
        """Sync cached layer info from the animation loop."""
        self._layers = []

        if self._animgr._loop is None:
            return

        for holder in self._animgr._loop.layers:
            self._layers.append(
                {
                    "type": holder.type_string,
                    "zindex": holder.zindex,
                    "layer": holder.renderer,
                }
            )

    def _layers_changed(self, action, zindex=None, layer=None):
        if action in {"add", "remove", "modify"}:
            self._sync_layers()

        self.emit_properties_changed({"CurrentRenderers": self.CurrentRenderers})

    def _state_changed(self, state):
        self._state = state
        self._logger.debug("_state_changed: %s", state)
        self.emit_properties_changed({"AnimationState": state})

    @dbus_property(access=PropertyAccess.READ)
    def AvailableRenderers(self) -> "a{sa{sv}}":
        avail = {}
        infos = self._animgr.renderer_info
        for key, info in infos.items():
            # Inner dict values need to be Variants for a{sv} signature
            avail[key] = dbus_prepare({"meta": info.meta, "traits": info.traits}, variant=True)[0]
        return avail

    @dbus_property(access=PropertyAccess.READ)
    def CurrentRenderers(self) -> "a(so)":
        path = self._device_api.bus_path
        return [
            (info["type"], f"{path}/layer/{info['zindex']}")
            for info in sorted(self._layers, key=lambda z: z["zindex"])
        ]

    @dbus_property(access=PropertyAccess.READ)
    def AnimationState(self) -> "s":
        return self._state or ""

    @method()
    def GetCurrentFrame(self) -> "a{sv}":
        frame = getattr(self._driver, "frame_control", None)
        if frame is None or frame.last_frame is None:
            return {}

        img = frame.last_frame
        if img.dtype != np.uint8:
            img = img.astype(np.uint8)

        height, width = img.shape[:2]
        return {
            "width": Variant("i", int(width)),
            "height": Variant("i", int(height)),
            "data": Variant("ay", img.tobytes()),
            "seq": Variant("i", int(frame.frame_seq)),
            "timestamp": Variant("d", float(frame.last_frame_ts)),
        }

    @method()
    def AddRenderer(self, name: "s", zindex: "i", traits: "a{sv}") -> "o":
        self._logger.debug("AddRenderer: name=%s zindex=%d traits=%s", name, zindex, traits)
        if zindex < 0:
            zindex = None

        # Extract values from variants
        kwargs = {k: (v.value if isinstance(v, Variant) else v) for k, v in traits.items()}
        z = self._animgr.add_renderer(name, traits=kwargs, zindex=zindex)
        if z >= 0:
            return f"{self._device_api.bus_path}/layer/{z}"
        return "/"

    @method()
    def GetLayerInfo(self, zindex: "i") -> "a{sv}":
        """Get info about a layer by zindex."""
        for info in self._layers:
            if info["zindex"] == zindex:
                layer = info["layer"]
                result = {
                    "Key": info["type"],
                    "ZIndex": zindex,
                    "Type": info["type"],
                }
                # Add trait values
                if hasattr(layer, "traits"):
                    from uchroma.traits import get_args_dict  # noqa: PLC0415

                    result.update(get_args_dict(layer))
                prepared, _sig = dbus_prepare(result, variant=True)
                return prepared
        return {}

    @method()
    def SetLayerTraits(self, zindex: "i", traits: "a{sv}") -> "b":
        """Set renderer traits for a layer by zindex."""
        self._logger.debug("SetLayerTraits: zindex=%d traits=%s", zindex, traits)
        for info in self._layers:
            if info["zindex"] == zindex:
                layer = info["layer"]
                for k, v in traits.items():
                    if not hasattr(layer, "has_trait") or not layer.has_trait(k):
                        self._logger.debug("SetLayerTraits: skipping %s (no trait)", k)
                        continue
                    val = v.value if isinstance(v, Variant) else v
                    self._logger.debug("SetLayerTraits: setting %s=%s on %s", k, val, layer)
                    setattr(layer, k, val)
                return True
        self._logger.debug("SetLayerTraits: no layer found with zindex=%d", zindex)
        return False

    @method()
    def RemoveRenderer(self, zindex: "i") -> "b":
        return self._animgr.remove_renderer(zindex)

    @method()
    def StopAnimation(self) -> "b":
        return self._animgr.stop()

    @method()
    def PauseAnimation(self) -> "b":
        return self._animgr.pause()


class SystemControlInterface(ServiceInterface):
    """
    D-Bus interface for laptop system control (fan, power modes, boost).
    Only available on Razer Blade laptops.
    """

    def __init__(self, driver):
        super().__init__("io.uchroma.SystemControl")
        self._driver = driver
        self._logger = driver.logger

        # Note: D-Bus property changes are handled automatically by dbus-fast
        # when properties are set through D-Bus setters. The driver signals
        # (fan_changed, power_mode_changed) are for internal use and don't
        # need to trigger D-Bus notifications when the change came from D-Bus.

    # ─────────────────────────────────────────────────────────────────────────
    # Fan Control
    # ─────────────────────────────────────────────────────────────────────────

    @dbus_property(access=PropertyAccess.READ)
    def FanRPM(self) -> "ai":
        """Current fan RPM(s). Returns [fan1] or [fan1, fan2] for dual-fan models."""
        rpm1, rpm2 = self._driver.fan_rpm
        if rpm2 is not None:
            return [rpm1, rpm2]
        return [rpm1]

    @dbus_property(access=PropertyAccess.READ)
    def FanMode(self) -> "s":
        """Current fan mode: 'auto' or 'manual'."""
        return self._driver.fan_mode.name.lower()

    @dbus_property(access=PropertyAccess.READ)
    def FanLimits(self) -> "a{sv}":
        """Fan RPM limits for this model."""
        limits = self._driver.fan_limits
        return {
            "min_rpm": Variant("i", limits.min_rpm),
            "min_manual_rpm": Variant("i", limits.min_manual_rpm),
            "max_rpm": Variant("i", limits.max_rpm),
            "supports_dual_fan": Variant("b", limits.supports_dual_fan),
        }

    @method()
    def SetFanAuto(self) -> "b":
        """Set fans to automatic EC control."""
        return self._driver.set_fan_auto()

    @method()
    def SetFanRPM(self, rpm: "i", fan2_rpm: "i") -> "b":
        """Set manual fan RPM. Use fan2_rpm=-1 to ignore second fan."""
        try:
            fan2 = fan2_rpm if fan2_rpm >= 0 else None
            return self._driver.set_fan_rpm(rpm, fan2)
        except ValueError as e:
            self._logger.warning("SetFanRPM failed: %s", e)
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # Power Modes
    # ─────────────────────────────────────────────────────────────────────────

    @dbus_property()
    def PowerMode(self) -> "s":
        """Current power mode: balanced, gaming, creator, or custom."""
        return self._driver.power_mode.name.lower()

    @PowerMode.setter
    def PowerMode(self, mode: "s"):
        """Set power mode by name."""
        try:
            self._driver.power_mode = PowerMode[mode.upper()]
        except KeyError:
            self._logger.warning("Unknown power mode: %s", mode)

    @dbus_property(access=PropertyAccess.READ)
    def AvailablePowerModes(self) -> "as":
        """List of available power modes."""
        return [m.name.lower() for m in PowerMode]

    # ─────────────────────────────────────────────────────────────────────────
    # Boost Control
    # ─────────────────────────────────────────────────────────────────────────

    @dbus_property()
    def CPUBoost(self) -> "s":
        """Current CPU boost mode: low, medium, high, or boost."""
        return self._driver.cpu_boost.name.lower()

    @CPUBoost.setter
    def CPUBoost(self, mode: "s"):
        """Set CPU boost mode (requires custom power mode)."""
        try:
            self._driver.cpu_boost = BoostMode[mode.upper()]
        except KeyError:
            self._logger.warning("Unknown boost mode: %s", mode)

    @dbus_property()
    def GPUBoost(self) -> "s":
        """Current GPU boost mode: low, medium, high, or boost."""
        return self._driver.gpu_boost.name.lower()

    @GPUBoost.setter
    def GPUBoost(self, mode: "s"):
        """Set GPU boost mode (requires custom power mode)."""
        try:
            self._driver.gpu_boost = BoostMode[mode.upper()]
        except KeyError:
            self._logger.warning("Unknown boost mode: %s", mode)

    @dbus_property(access=PropertyAccess.READ)
    def AvailableBoostModes(self) -> "as":
        """List of available boost modes (empty if device doesn't support boost)."""
        if not self._driver.supports_boost:
            return []
        return [m.name.lower() for m in BoostMode]

    # ─────────────────────────────────────────────────────────────────────────
    # Capability Flags
    # ─────────────────────────────────────────────────────────────────────────

    @dbus_property(access=PropertyAccess.READ)
    def SupportsFanSpeed(self) -> "b":
        """True if device supports real-time fan RPM reading."""
        return self._driver.supports_fan_speed

    @dbus_property(access=PropertyAccess.READ)
    def SupportsBoost(self) -> "b":
        """True if device supports CPU/GPU boost control."""
        return self._driver.supports_boost


class DeviceManagerInterface(ServiceInterface):
    """
    D-Bus interface for device manager (root service).
    """

    def __init__(self):
        super().__init__("io.uchroma.DeviceManager")
        self._device_paths = []

    def set_device_paths(self, paths: list):
        self._device_paths = paths

    @method()
    def GetDevices(self) -> "ao":
        return self._device_paths

    @signal()
    def DevicesChanged(self, action: "s", device: "o") -> "so":
        return [action, device]


class ObjectManagerInterface(ServiceInterface):
    """
    D-Bus ObjectManager interface for device discovery and introspection.
    """

    def __init__(self, manager_api):
        super().__init__("org.freedesktop.DBus.ObjectManager")
        self._manager_api = manager_api

    @method()
    def GetManagedObjects(self) -> "a{oa{sa{sv}}}":
        return self._manager_api.build_managed_objects()

    @signal()
    def InterfacesAdded(
        self, object_path: "o", interfaces_and_properties: "a{sa{sv}}"
    ) -> "oa{sa{sv}}":
        return [object_path, interfaces_and_properties]

    @signal()
    def InterfacesRemoved(self, object_path: "o", interfaces: "as") -> "oas":
        return [object_path, interfaces]


class DeviceAPI:
    """
    Manages D-Bus interfaces for a single device.
    """

    def __init__(self, driver, bus):
        self._driver = driver
        self._bus = bus
        self._logger = driver.logger
        self._interfaces = []
        self._published = False

        self.publish_changed = Signal()

    @property
    def bus_path(self):
        return f"/io/uchroma/{self._driver.device_type.value}/{self._driver.vendor_id:04x}_{self._driver.product_id:04x}_{self._driver.device_index:02d}"

    @property
    def driver(self):
        return self._driver

    def interface_map(self) -> dict:
        return {iface.name: _interface_properties(iface) for iface in self._interfaces}

    def interface_names(self) -> list[str]:
        return [iface.name for iface in self._interfaces]

    def publish(self):
        if self._published:
            return

        # Create main device interface
        device_iface = DeviceInterface(self._driver, self)
        self._interfaces.append(device_iface)

        # Add optional manager interfaces
        if hasattr(self._driver, "fx_manager") and self._driver.fx_manager is not None:
            self._interfaces.append(FXManagerInterface(self._driver))

        if (
            hasattr(self._driver, "animation_manager")
            and self._driver.animation_manager is not None
        ):
            self._interfaces.append(AnimationManagerInterface(self._driver, self))

        if hasattr(self._driver, "led_manager") and self._driver.led_manager is not None:
            self._interfaces.append(LEDManagerInterface(self._driver))

        # Add system control interface for laptops
        if (
            hasattr(self._driver, "supports_system_control")
            and self._driver.supports_system_control
        ):
            self._interfaces.append(SystemControlInterface(self._driver))

        # Export all interfaces on same path
        for iface in self._interfaces:
            self._bus.export(self.bus_path, iface)

        self._published = True
        self.publish_changed.fire(True)
        self._logger.info("Published device at %s", self.bus_path)

    def unpublish(self):
        if not self._published:
            return

        self.publish_changed.fire(False)

        for iface in self._interfaces:
            self._bus.unexport(self.bus_path, iface)

        self._interfaces.clear()
        self._published = False
        self._logger.info("Unpublished device at %s", self.bus_path)


class DeviceManagerAPI:
    """
    Main D-Bus service manager.
    """

    def __init__(self, device_manager, logger):
        self._dm = device_manager
        self._logger = logger
        self._bus = None
        self.ready = asyncio.Event()
        self._dm.callbacks.append(self._dm_callback)
        self._devs = OrderedDict()
        self._manager_iface = None
        self._object_manager_iface = None

    def _publish_device(self, device):
        devapi = DeviceAPI(device, self._bus)
        devapi.publish()
        self._devs[device.key] = devapi
        self._update_device_paths()
        if self._object_manager_iface is not None:
            self._object_manager_iface.InterfacesAdded(devapi.bus_path, devapi.interface_map())
        return devapi.bus_path

    def _unpublish_device(self, device):
        devapi = self._devs.pop(device.key, None)
        if devapi is not None:
            interfaces = devapi.interface_names()
            devapi.unpublish()
            self._update_device_paths()
            if self._object_manager_iface is not None and interfaces:
                self._object_manager_iface.InterfacesRemoved(devapi.bus_path, interfaces)
            return devapi.bus_path
        return None

    def _update_device_paths(self):
        if self._manager_iface:
            self._manager_iface.set_device_paths([x.bus_path for x in self._devs.values()])

    def build_managed_objects(self) -> dict:
        root_ifaces = {}
        if self._manager_iface is not None:
            root_ifaces[self._manager_iface.name] = _interface_properties(self._manager_iface)

        managed = {ROOT_PATH: root_ifaces}
        for devapi in self._devs.values():
            managed[devapi.bus_path] = devapi.interface_map()
        return managed

    async def _dm_callback(self, action, device):
        self._logger.info("%s: %s", action, device)

        path = None

        if action == "add":
            path = self._publish_device(device)
            device.fire_restore_prefs()

        elif action == "remove":
            path = self._unpublish_device(device)

        else:
            return

        if path is not None:
            self._manager_iface.DevicesChanged(action, path)

    async def run(self):
        """
        Connect to D-Bus and publish the service.
        """
        self._bus = await MessageBus(bus_type=BusType.SESSION).connect()

        # Create and export manager interface
        self._manager_iface = DeviceManagerInterface()
        self._object_manager_iface = ObjectManagerInterface(self)
        self._bus.export(ROOT_PATH, self._manager_iface)
        self._bus.export(ROOT_PATH, self._object_manager_iface)

        # Request the bus name
        await self._bus.request_name(BUS_NAME)

        self._logger.info("D-Bus service published as %s", BUS_NAME)
        self.ready.set()

        # Keep the connection alive
        await self._bus.wait_for_disconnect()

    def run_sync(self):
        """
        Synchronous entry point for running the D-Bus service.
        """
        asyncio.run(self.run())
