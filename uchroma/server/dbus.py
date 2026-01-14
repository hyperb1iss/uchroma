#
# uchroma - Copyright (C) 2021 Stefanie Kondik
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#

# pylint: disable=invalid-name,protected-access
# ruff: noqa: F821, F722 - D-Bus type annotations are strings like 's', 'd', etc.

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

from dbus_fast import BusType, PropertyAccess, Variant
from dbus_fast.aio import MessageBus
from dbus_fast.service import ServiceInterface, dbus_property, method, signal

from uchroma.dbus_utils import dbus_prepare
from uchroma.util import Signal

from .types import LEDType


def dev_mode_enabled():
    return os.environ.get('UCHROMA_DEV') is not None


BUS_NAME = 'org.chemlab.UChroma'


class DeviceInterface(ServiceInterface):
    """
    D-Bus interface for device properties and common hardware features.
    """

    def __init__(self, driver, device_api):
        super().__init__('org.chemlab.UChroma.Device')
        self._driver = driver
        self._device_api = device_api
        self._logger = driver.logger
        self._signal_input = False
        self._input_task = None
        self._input_queue = None

    # Read-only properties
    @dbus_property(access=PropertyAccess.READ)
    def Name(self) -> 's':
        return self._driver.name or ''

    @dbus_property(access=PropertyAccess.READ)
    def DeviceType(self) -> 's':
        dt = self._driver.device_type
        return dt.name.lower() if isinstance(dt, Enum) else str(dt)

    @dbus_property(access=PropertyAccess.READ)
    def DriverVersion(self) -> 's':
        return getattr(self._driver, 'driver_version', '') or ''

    @dbus_property(access=PropertyAccess.READ)
    def FirmwareVersion(self) -> 's':
        return getattr(self._driver, 'firmware_version', '') or ''

    @dbus_property(access=PropertyAccess.READ)
    def SerialNumber(self) -> 's':
        return getattr(self._driver, 'serial_number', '') or ''

    @dbus_property(access=PropertyAccess.READ)
    def Manufacturer(self) -> 's':
        return getattr(self._driver, 'manufacturer', '') or ''

    @dbus_property(access=PropertyAccess.READ)
    def VendorId(self) -> 'u':
        return self._driver.vendor_id or 0

    @dbus_property(access=PropertyAccess.READ)
    def ProductId(self) -> 'u':
        return self._driver.product_id or 0

    @dbus_property(access=PropertyAccess.READ)
    def DeviceIndex(self) -> 'u':
        return getattr(self._driver, 'device_index', 0) or 0

    @dbus_property(access=PropertyAccess.READ)
    def HasMatrix(self) -> 'b':
        return getattr(self._driver, 'has_matrix', False)

    @dbus_property(access=PropertyAccess.READ)
    def Width(self) -> 'i':
        return getattr(self._driver, 'width', 0) or 0

    @dbus_property(access=PropertyAccess.READ)
    def Height(self) -> 'i':
        return getattr(self._driver, 'height', 0) or 0

    @dbus_property(access=PropertyAccess.READ)
    def SysPath(self) -> 's':
        return getattr(self._driver, 'sys_path', '') or ''

    @dbus_property(access=PropertyAccess.READ)
    def Key(self) -> 's':
        return getattr(self._driver, 'key', '') or ''

    @dbus_property(access=PropertyAccess.READ)
    def BusPath(self) -> 'o':
        return self._device_api.bus_path

    @dbus_property(access=PropertyAccess.READ)
    def IsWireless(self) -> 'b':
        return getattr(self._driver, 'is_wireless', False)

    @dbus_property(access=PropertyAccess.READ)
    def IsCharging(self) -> 'b':
        return getattr(self._driver, 'is_charging', False)

    @dbus_property(access=PropertyAccess.READ)
    def BatteryLevel(self) -> 'd':
        return getattr(self._driver, 'battery_level', 0.0) or 0.0

    @dbus_property(access=PropertyAccess.READ)
    def SupportedLeds(self) -> 'as':
        leds = getattr(self._driver, 'supported_leds', [])
        return [x.name.lower() for x in leds]

    @dbus_property(access=PropertyAccess.READ)
    def Zones(self) -> 'as':
        zones = getattr(self._driver, 'zones', [])
        if isinstance(zones, (list, tuple)):
            return [str(z) for z in zones]
        return []

    # Read-write properties
    @dbus_property()
    def Brightness(self) -> 'd':
        return getattr(self._driver, 'brightness', 0.0) or 0.0

    @Brightness.setter
    def Brightness(self, value: 'd'):
        if value < 0.0 or value > 100.0:
            return
        old = self._driver.brightness
        self._driver.brightness = value
        if old != self._driver.brightness:
            self.emit_properties_changed({'Brightness': value})

    @dbus_property()
    def Suspended(self) -> 'b':
        return getattr(self._driver, 'suspended', False)

    @Suspended.setter
    def Suspended(self, value: 'b'):
        current = getattr(self._driver, 'suspended', False)
        if value == current:
            return
        if value:
            self._driver.suspend()
        else:
            self._driver.resume()
        if current != self._driver.suspended:
            self.emit_properties_changed({'Suspended': self._driver.suspended})

    @method()
    def Reset(self):
        self._driver.reset()

    @signal()
    def PropertiesChanged(self, interface_name: 's', changed_properties: 'a{sv}',
                          invalidated_properties: 'as') -> 'sa{sv}as':
        return [interface_name, changed_properties, invalidated_properties]

    def emit_properties_changed(self, changed: dict):
        props = {k: Variant('d' if isinstance(v, float) else 'b', v) for k, v in changed.items()}
        self.PropertiesChanged('org.chemlab.UChroma.Device', props, [])


class LEDManagerInterface(ServiceInterface):
    """
    D-Bus interface for LED management.
    """

    def __init__(self, driver):
        super().__init__('org.chemlab.UChroma.LEDManager')
        self._driver = driver
        self._logger = driver.logger
        self._driver.led_manager.led_changed.connect(self._led_changed)

    def _led_changed(self, led):
        self.LEDChanged(led.led_type.name.lower())

    @dbus_property(access=PropertyAccess.READ)
    def AvailableLEDs(self) -> 'a{sa{sv}}':
        leds = {}
        for led in self._driver.led_manager.supported_leds:
            led_obj = self._driver.led_manager.get(led)
            traits = led_obj._trait_values if hasattr(led_obj, '_trait_values') else {}
            # Inner dict values need to be Variants for a{sv} signature
            leds[led.name.lower()] = dbus_prepare(traits, variant=True)[0]
        return leds

    @method()
    def GetLED(self, name: 's') -> 'a{sv}':
        try:
            ledtype = LEDType[name.upper()]
        except KeyError:
            self._logger.error("Unknown LED type: %s", name)
            return {}
        led = self._driver.led_manager.get(ledtype)
        return dbus_prepare(led._trait_values, variant=True)[0]

    @method()
    def SetLED(self, name: 's', properties: 'a{sv}') -> 'b':
        try:
            ledtype = LEDType[name.upper()]
        except KeyError:
            self._logger.error("Unknown LED type: %s", name)
            return False

        led = self._driver.led_manager.get(ledtype)
        with led.hold_trait_notifications():
            self._logger.debug('Set LED property [%s]: %s', ledtype, properties)
            for k, v in properties.items():
                if led.has_trait(k):
                    # Extract value from Variant if needed
                    val = v.value if isinstance(v, Variant) else v
                    setattr(led, k, val)
        return True

    @signal()
    def LEDChanged(self, led: 's') -> 's':
        return led


class FXManagerInterface(ServiceInterface):
    """
    D-Bus interface for built-in effects.
    """

    def __init__(self, driver):
        super().__init__('org.chemlab.UChroma.FXManager')
        self._driver = driver
        self._logger = driver.logger
        self._fx_manager = driver.fx_manager

        self._current_fx = None
        # Build simplified FX metadata - each FX has a dict of trait_name -> type info
        self._available_fx = {}
        for fx_name, fx_class in self._fx_manager.available_fx.items():
            fx_info = {}
            for trait_name, trait_type in fx_class.class_traits().items():
                # Simple type info as Variant
                type_name = trait_type.__class__.__name__
                fx_info[trait_name] = Variant('s', type_name)
            self._available_fx[fx_name] = fx_info

        self._fx_manager.observe(self._fx_changed, names=['current_fx'])

    def _fx_changed(self, change):
        self._logger.info("Effects changed: %s", change)
        self._current_fx = (change.new[0].lower(),
                           dbus_prepare(change.new[1]._trait_values, variant=True)[0])
        self.emit_properties_changed({'CurrentFX': self.CurrentFX})

    @dbus_property(access=PropertyAccess.READ)
    def AvailableFX(self) -> 'a{sa{sv}}':
        return self._available_fx

    @dbus_property(access=PropertyAccess.READ)
    def CurrentFX(self) -> '(sa{sv})':
        if self._current_fx is None:
            return ('disable', {})
        return self._current_fx

    @method()
    def SetFX(self, name: 's', args: 'a{sv}') -> 'b':
        # Extract values from variants
        kwargs = {k: (v.value if isinstance(v, Variant) else v) for k, v in args.items()}
        return self._fx_manager.activate(name, **kwargs)

    @signal()
    def PropertiesChanged(self, interface_name: 's', changed_properties: 'a{sv}',
                          invalidated_properties: 'as') -> 'sa{sv}as':
        return [interface_name, changed_properties, invalidated_properties]

    def emit_properties_changed(self, changed: dict):
        # FX uses tuple, serialize appropriately
        props = {}
        for k, v in changed.items():
            if isinstance(v, tuple) and len(v) == 2:
                props[k] = Variant('(sa{sv})', v)
            else:
                props[k] = Variant('s', str(v))
        self.PropertiesChanged('org.chemlab.UChroma.FXManager', props, [])


class AnimationManagerInterface(ServiceInterface):
    """
    D-Bus interface for animation/renderer management.
    """

    def __init__(self, driver, device_api):
        super().__init__('org.chemlab.UChroma.AnimationManager')
        self._driver = driver
        self._device_api = device_api
        self._logger = driver.logger
        self._animgr = driver.animation_manager
        self._layers = []
        self._state = None

        self._animgr.layers_changed.connect(self._layers_changed)
        self._animgr.state_changed.connect(self._state_changed)

    def _layers_changed(self, action, zindex=None, layer=None):
        if action == 'add' and layer is not None:
            layer_info = {
                'type': '%s.%s' % (layer.__class__.__module__, layer.__class__.__name__),
                'zindex': layer.zindex,
                'layer': layer
            }
            self._layers.append(layer_info)

        self.emit_properties_changed({'CurrentRenderers': self.CurrentRenderers})

    def _state_changed(self, state):
        self._state = state
        self._logger.debug("_state_changed: %s", state)
        self.emit_properties_changed({'AnimationState': state})

    @dbus_property(access=PropertyAccess.READ)
    def AvailableRenderers(self) -> 'a{sa{sv}}':
        avail = {}
        infos = self._animgr.renderer_info
        for key, info in infos.items():
            # Inner dict values need to be Variants for a{sv} signature
            avail[key] = dbus_prepare({'meta': info.meta, 'traits': info.traits}, variant=True)[0]
        return avail

    @dbus_property(access=PropertyAccess.READ)
    def CurrentRenderers(self) -> 'a(so)':
        path = self._device_api.bus_path
        return [(info['type'], '%s/layer/%d' % (path, info['zindex']))
                for info in sorted(self._layers, key=lambda z: z['zindex'])]

    @dbus_property(access=PropertyAccess.READ)
    def AnimationState(self) -> 's':
        return self._state or ''

    @method()
    def AddRenderer(self, name: 's', zindex: 'i', traits: 'a{sv}') -> 'o':
        self._logger.debug('AddRenderer: name=%s zindex=%d traits=%s', name, zindex, traits)
        if zindex < 0:
            zindex = None

        # Extract values from variants
        kwargs = {k: (v.value if isinstance(v, Variant) else v) for k, v in traits.items()}
        z = self._animgr.add_renderer(name, traits=kwargs, zindex=zindex)
        if z >= 0:
            return '%s/layer/%d' % (self._device_api.bus_path, z)
        return '/'

    @method()
    def RemoveRenderer(self, zindex: 'i') -> 'b':
        return self._animgr.remove_renderer(zindex)

    @method()
    def StopAnimation(self) -> 'b':
        return self._animgr.stop()

    @method()
    def PauseAnimation(self) -> 'b':
        return self._animgr.pause()

    @signal()
    def PropertiesChanged(self, interface_name: 's', changed_properties: 'a{sv}',
                          invalidated_properties: 'as') -> 'sa{sv}as':
        return [interface_name, changed_properties, invalidated_properties]

    def emit_properties_changed(self, changed: dict):
        props = {}
        for k, v in changed.items():
            if isinstance(v, list):
                props[k] = Variant('a(so)', v)
            else:
                props[k] = Variant('s', str(v))
        self.PropertiesChanged('org.chemlab.UChroma.AnimationManager', props, [])


class DeviceManagerInterface(ServiceInterface):
    """
    D-Bus interface for device manager (root service).
    """

    def __init__(self):
        super().__init__('org.chemlab.UChroma.DeviceManager')
        self._device_paths = []

    def set_device_paths(self, paths: list):
        self._device_paths = paths

    @method()
    def GetDevices(self) -> 'ao':
        return self._device_paths

    @signal()
    def DevicesChanged(self, action: 's', device: 'o') -> 'so':
        return [action, device]


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
        return '/org/chemlab/UChroma/%s/%04x_%04x_%02d' % (
            self._driver.device_type.value, self._driver.vendor_id,
            self._driver.product_id, self._driver.device_index)

    @property
    def driver(self):
        return self._driver

    def publish(self):
        if self._published:
            return

        # Create main device interface
        device_iface = DeviceInterface(self._driver, self)
        self._interfaces.append(device_iface)

        # Add optional manager interfaces
        if hasattr(self._driver, 'fx_manager') and self._driver.fx_manager is not None:
            self._interfaces.append(FXManagerInterface(self._driver))

        if hasattr(self._driver, 'animation_manager') and self._driver.animation_manager is not None:
            self._interfaces.append(AnimationManagerInterface(self._driver, self))

        if hasattr(self._driver, 'led_manager') and self._driver.led_manager is not None:
            self._interfaces.append(LEDManagerInterface(self._driver))

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
        self._dm.callbacks.append(self._dm_callback)
        self._devs = OrderedDict()
        self._manager_iface = None

    def _publish_device(self, device):
        devapi = DeviceAPI(device, self._bus)
        devapi.publish()
        self._devs[device.key] = devapi
        self._update_device_paths()
        return devapi.bus_path

    def _unpublish_device(self, device):
        devapi = self._devs.pop(device.key, None)
        if devapi is not None:
            devapi.unpublish()
            self._update_device_paths()
            return devapi.bus_path
        return None

    def _update_device_paths(self):
        if self._manager_iface:
            self._manager_iface.set_device_paths([x.bus_path for x in self._devs.values()])

    async def _dm_callback(self, action, device):
        self._logger.info('%s: %s', action, device)

        path = None

        if action == 'add':
            path = self._publish_device(device)
            device.fire_restore_prefs()

        elif action == 'remove':
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
        self._bus.export('/org/chemlab/UChroma', self._manager_iface)

        # Request the bus name
        await self._bus.request_name(BUS_NAME)

        self._logger.info("D-Bus service published as %s", BUS_NAME)

        # Keep the connection alive
        await self._bus.wait_for_disconnect()

    def run_sync(self):
        """
        Synchronous entry point for running the D-Bus service.
        """
        asyncio.run(self.run())
