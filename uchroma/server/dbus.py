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

"""
D-Bus interfaces

These interfaces are designed to exist as a separate layer
and do not contain recursive dependencies with the lower
layers. UI clients should be designed to use these interfaces
rather than interacting with the hardware directly.
"""

import logging
import os

from collections import OrderedDict
from enum import Enum

from pydbus import SessionBus
from pydbus.generic import signal

from grapefruit import Color

from uchroma.dbus_utils import ArgSpec, dbus_prepare, DescriptorBuilder, \
        TraitsPropertiesMixin
from uchroma.input_queue import InputQueue
from uchroma.util import camel_to_snake, ensure_future, snake_to_camel, Signal

from .types import LEDType


def dev_mode_enabled():
    return os.environ.get('UCHROMA_DEV') is not None


class ManagedService:
    def __init__(self, parent, *args, **kwargs):
        super(ManagedService, self).__init__(*args, **kwargs)

        self._driver = parent.driver
        self._logger = parent.driver.logger
        self._path = parent.bus_path
        self._bus = parent.bus
        self._handle = None

        parent.publish_changed.connect(self._publish_changed)

        if parent._handle is not None:
            self._publish_changed(True)


    def publish(self):
        if self._handle is None:
            self._handle = self._bus.register_object(self._path, self, None)


    def unpublish(self):
        if self._handle is not None:
            self._handle.unregister()
            self._handle = None
            return True
        return False


    def _publish_changed(self, published):
        if published:
            self.publish()
        else:
            self.unpublish()


class DeviceAPI:
    """
    D-Bus API for device properties and common hardware features.
    """

    if dev_mode_enabled():
        InputEvent = signal()


    _PROPERTIES = {'battery_level': 'd',
                   'bus_path': 'o',
                   'device_index': 'u',
                   'device_type': 's',
                   'driver_version': 's',
                   'firmware_version': 's',
                   'has_matrix': 'b',
                   'height': 'i',
                   'is_charging': 'b',
                   'is_wireless': 'b',
                   'key': 's',
                   'manufacturer': 's',
                   'name': 's',
                   'product_id': 'u',
                   'revision': 'u',
                   'serial_number': 's',
                   'key_mapping': 'a{saau}',
                   'sys_path': 's',
                   'vendor_id': 'u',
                   'width': 'i',
                   'zones': 'as'}


    _RW_PROPERTIES = {'polling_rate': 's',
                      'dpi_xy': 'ai',
                      'dock_brightness': 'd',
                      'dock_charge_color': 's'}


    def __init__(self, driver, bus):
        self._driver = driver
        self._bus = bus
        self._logger = driver.logger
        self.__class__.dbus = self._get_descriptor()
        self._signal_input = False
        self._input_task = None
        self._input_queue = None
        self._services = []
        self._handle = None

        self.publish_changed = Signal()

        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug('Device API attached: %s', self.__class__.dbus)


    def __getattribute__(self, name):
        # Intercept everything and delegate to the device class by converting
        # names between the D-Bus conventions to Python conventions.
        prop_name = camel_to_snake(name)
        if (prop_name in DeviceAPI._PROPERTIES or prop_name in DeviceAPI._RW_PROPERTIES) \
                and hasattr(self._driver, prop_name):
            value = getattr(self._driver, prop_name)
            if isinstance(value, Enum):
                return value.name.lower()
            if isinstance(value, Color):
                return value.html
            if isinstance(value, (list, tuple)) and value and isinstance(value[0], Enum):
                return [x.name.lower() for x in value]
            return value

        return super(DeviceAPI, self).__getattribute__(name)


    def __setattr__(self, name, value):
        prop_name = camel_to_snake(name)
        if prop_name != name and prop_name in DeviceAPI._RW_PROPERTIES:
            setattr(self._driver, prop_name, value)
        else:
            super(DeviceAPI, self).__setattr__(name, value)


    @property
    def bus_path(self):
        """
        Get the bus path for all services related to this device.
        """
        return '/org/chemlab/UChroma/%s/%04x_%04x_%02d' % \
            (self._driver.device_type.value, self._driver.vendor_id,
             self._driver.product_id, self._driver.device_index)


    @property
    def bus(self):
        return self._bus


    @property
    def driver(self):
        return self._driver


    def publish(self):
        if self._handle is not None:
            return

        self._handle = self._bus.register_object(self.bus_path, self, None)

        if hasattr(self.driver, 'fx_manager') and self.driver.fx_manager is not None:
            self._services.append(FXManagerAPI(self))

        if hasattr(self.driver, 'animation_manager') and self.driver.animation_manager is not None:
            self._services.append(AnimationManagerAPI(self))

        if hasattr(self.driver, 'led_manager') and self.driver.led_manager is not None:
            self._services.append(LEDManagerAPI(self))

        self.publish_changed.fire(True)


    def unpublish(self):
        if self._handle is None:
            return

        self.publish_changed.fire(False)

        self._handle.unregister()
        self._handle = None


    async def _dev_mode_input(self):
        while self._signal_input:
            event = await self._input_queue.get_events()
            if event is not None:
                self.InputEvent(dbus_prepare(event)[0])


    @property
    def SupportedLeds(self) -> list:
        return [x.name.lower() for x in self._driver.supported_leds]


    @property
    def InputSignalEnabled(self) -> bool:
        """
        Enabling input signalling will fire D-Bus signals when keyboard
        input is received. This is used by the tooling and bringup
        utilities. Developer mode must be enabled in order for this
        to be available on the bus due to potential security issues.
        """
        return self._signal_input


    @InputSignalEnabled.setter
    def InputSignalEnabled(self, state):
        if dev_mode_enabled():
            if state == self._signal_input:
                return

            if state:
                if self._input_queue is None:
                    self._input_queue = InputQueue(self._driver)
                self._input_queue.attach()
                self._input_task = ensure_future(self._dev_mode_input())
            else:
                ensure_future(self._input_queue.detach())
                self._input_task.cancel()

                self._input_queue = None

            self._signal_input = state


    @property
    def FrameDebugOpts(self) -> dict:
        return dbus_prepare(self._driver.frame_control.debug_opts, variant=True)[0]


    PropertiesChanged = signal()


    @property
    def Brightness(self):
        """
        The current brightness level
        """
        return self._driver.brightness


    @Brightness.setter
    def Brightness(self, value):
        """
        Set the brightness level of the device lighting.
        0.0 - 100.0
        """
        if value < 0.0 or value > 100.0:
            return

        old = self._driver.brightness
        self._driver.brightness = value
        if old != self._driver.brightness:
            self.PropertiesChanged('org.chemlab.UChroma.Device', {'Brightness': value}, [])


    @property
    def Suspended(self):
        """
        True if the device is suspended
        """
        return self._driver.suspended


    @Suspended.setter
    def Suspended(self, value):
        """
        Set the suspended state of the device
        """
        current = self._driver.suspended
        if value == current:
            return

        if value:
            self._driver.suspend()
        else:
            self._driver.resume()

        if current != self._driver.suspended:
            self.PropertiesChanged('org.chemlab.UChroma.Device', {'Suspended': self.Suspended}, [])


    def Reset(self):
        self._driver.reset()


    def _get_descriptor(self):
        builder = DescriptorBuilder(self, 'org.chemlab.UChroma.Device')
        for name, sig in DeviceAPI._PROPERTIES.items():
            if hasattr(self._driver, name):
                builder.add_property(name, sig, False)

        for name, sig in DeviceAPI._RW_PROPERTIES.items():
            if hasattr(self._driver, name):
                builder.add_property(name, sig, True)

        if hasattr(self._driver, 'brightness'):
            builder.add_property('brightness', 'd', True)

        if hasattr(self._driver, 'suspend') and hasattr(self._driver, 'resume'):
            builder.add_property('suspended', 'b', True)

        builder.add_method('reset')

        # tooling support, requires dev mode enabled
        if dev_mode_enabled() and self._driver.input_manager is not None:
            builder.add_property('frame_debug_opts', 'a{sv}', False)
            builder.add_property('input_signal_enabled', 'b', True)
            builder.add_signal('input_event', ArgSpec('out', 'event', 'a{sv}'))

        return builder.build()


class LEDManagerAPI(ManagedService):
    """
    <node>
        <interface name='org.chemlab.UChroma.LEDManager'>
            <property name='AvailableLEDs' type='a{sa{sa{sv}}}' access='read' />

            <method name='GetLED'>
                <arg direction='in' type='s' name='led' />
                <arg direction='out' type='a{sv}' name='properties' />
            </method>

            <method name='SetLED'>
                <arg direction='in' type='s' name='led' />
                <arg direction='in' type='a{sv}' name='properties' />
                <arg direction='out' type='b' name='status' />
            </method>

            <signal name='LEDChanged'>
                <arg direction='out' type='s' name='led' />
            </signal>
        </interface>
    </node>
    """

    def __init__(self, parent):
        super(LEDManagerAPI, self).__init__(parent)

        self._driver.led_manager.led_changed.connect(self._led_changed)


    def _led_changed(self, led):
        self.LEDChanged(led.led_type.name.lower())


    @property
    def AvailableLEDs(self):
        leds = {}
        for led in self._driver.led_manager.supported_leds:
            leds[led.name.lower()] = self._driver.led_manager.get(led).traits()

        return dbus_prepare(leds)[0]


    def GetLED(self, name: str) -> dict:
        ledtype = LEDType[name.upper()]
        if ledtype is None:
            self._logger.error("Unknown LED type: %s", name)
            return {}

        return dbus_prepare(self._driver.led_manager.get(ledtype)._trait_values)[0]


    def SetLED(self, name: str, properties: dict) -> bool:
        ledtype = LEDType[name.upper()]
        if ledtype is None:
            self._logger.error("Unknown LED type: %s", name)
            return False

        led = self._driver.led_manager.get(ledtype)

        with led.hold_trait_notifications():
            self._logger.debug('Set LED property [%s]: %s', ledtype, properties)
            for k, v in properties.items():
                if led.has_trait(k):
                    setattr(led, k, v)

        return True


    LEDChanged = signal()


class FXManagerAPI(ManagedService):
    """
    <node>
        <interface name='org.chemlab.UChroma.FXManager'>
            <method name='SetFX'>
                <arg direction='in' type='s' name='name' />
                <arg direction='in' type='a{sv}' name='args' />
                <arg direction='out' type='b' name='status' />
            </method>

            <property name='CurrentFX' type='(sa{sv})' access='read'>
                    <annotation name='org.freedesktop.DBus.Property.EmitsChangedSignal' value='true' />
            </property>

            <property name='AvailableFX' type='a{sa{sa{sv}}}' access='read' />
        </interface>
    </node>
    """

    def __init__(self, parent):
        super(FXManagerAPI, self).__init__(parent)

        self._fx_manager = self._driver.fx_manager

        self._current_fx = None
        self._available_fx = dbus_prepare({k: v.class_traits() \
                for k, v in self._fx_manager.available_fx.items()})[0]

        self._fx_manager.observe(self._fx_changed, names=['current_fx'])


    def _fx_changed(self, change):
        self._logger.info("Effects changed: %s", change)
        self._current_fx = (change.new[0].lower(),
                            dbus_prepare(change.new[1]._trait_values, variant=True)[0])
        self.PropertiesChanged('org.chemlab.UChroma.FXManager',
                               {'CurrentFX': self.CurrentFX}, [])


    @property
    def AvailableFX(self):
        return self._available_fx


    @property
    def CurrentFX(self):
        """
        Get the currently active FX and arguments
        """
        if self._current_fx is None:
            return ('disable', {})

        return self._current_fx


    def SetFX(self, name: str, args: dict) -> bool:
        """
        Set the desired FX, with options as a dict.
        """
        return self._fx_manager.activate(name, **args)


    PropertiesChanged = signal()


class LayerAPI(TraitsPropertiesMixin, ManagedService):

    def __init__(self, parent, layer, *args, **kwargs):
        self._delegate = layer
        self._zindex = layer.zindex

        super(LayerAPI, self).__init__(parent, *args, **kwargs)

        self.__class__.dbus = None

        self.layer_stopped = Signal()

        self._delegate.observe(self._z_changed, names=['zindex'])
        self._delegate.observe(self._state_changed, names=['running'])

    def _z_changed(self, change):
        if change.old != change.new:
            self.publish()


    def _state_changed(self, change):
        if change.old != change.new:
            if change.new:
                self.publish()
            elif self._handle is not None:
                self._logger.info("Layer stopped zindex=%d (%s)",
                                  self._zindex, self._delegate.meta)
                self.unpublish()
                self.layer_stopped.fire(self)


    @staticmethod
    def get_layer_path(path, zindex):
        return '%s/layer/%d' % (path, zindex)


    @property
    def layer_path(self):
        return LayerAPI.get_layer_path(self._path, self._zindex)


    @property
    def layer_type(self):
        return '%s.%s' % (self._delegate.__class__.__module__, self._delegate.__class__.__name__)


    @property
    def layer_zindex(self):
        return self._zindex


    def publish(self):
        if not self._delegate.running:
            return

        self.unpublish()

        self.__class__.dbus = self._get_descriptor()

        self._zindex = self._delegate.zindex
        self._handle = self._bus.register_object(self.layer_path, self, None)
        self._logger.info("Registered layer API: %s", self.layer_path)
        self._logger.debug('%s', self.__class__.dbus)



    def unpublish(self):
        if super().unpublish():
            self._logger.info("Unregisted layer API: %s", self.layer_path)


    def _get_descriptor(self):
        exclude = ('blend_mode', 'opacity')
        if self._delegate.zindex > 0:
            exclude = ('background_color',)

        builder = DescriptorBuilder(self._delegate, 'org.chemlab.UChroma.Layer', exclude)

        for k, v in self._delegate.meta._asdict().items():
            attrib = snake_to_camel(k)
            setattr(self, attrib, v)
            builder.add_property(attrib, 's')

        setattr(self, 'Key', '%s.%s' % (self._delegate.__module__,
                                        self._delegate.__class__.__name__))
        builder.add_property('Key', 's')

        return builder.build()


class AnimationManagerAPI(ManagedService):
    """
    <node>
        <interface name='org.chemlab.UChroma.AnimationManager'>
            <method name='AddRenderer'>
                <arg direction='in' type='s' name='name' />
                <arg direction='in' type='i' name='zindex' />
                <arg direction='in' type='a{sv}' name='traits' />
                <arg direction='out' type='o' name='layer' />
            </method>

            <method name='RemoveRenderer'>
                <arg direction='in' type='i' name='zindex' />
                <arg direction='out' type='b' name='status' />
            </method>

            <method name='PauseAnimation'>
                <arg direction='out' type='b' name='paused' />
            </method>

            <method name='StopAnimation'>
                <arg direction='out' type='b' name='status' />
            </method>

            <property name='AvailableRenderers' type='a{sa{sv}}' access='read' />

            <property name='CurrentRenderers' type='a(so)' access='read'>
                <annotation name='org.freedesktop.DBus.Property.EmitsChangedSignal' value='true' />
            </property>

            <property name='AnimationState' type='s' access='read'>
                <annotation name='org.freedesktop.DBus.Property.EmitsChangedSignal' value='true' />
            </property>
        </interface>
    </node>
    """

    def __init__(self, parent):
        super(AnimationManagerAPI, self).__init__(parent)

        assert self._driver.animation_manager is not None, \
                'Animations not supported for this device'

        self._parent = parent
        self._animgr = self._driver.animation_manager
        self._layers = []
        self._state = None

        # manually notify, startup order isn't guaranteed
        self._animgr.layers_changed.connect(self._layers_changed)
        self._animgr.state_changed.connect(self._state_changed)


    PropertiesChanged = signal()


    def _layer_stopped(self, layer):
        del self._layers[self._layers.index(layer)]


    def _layers_changed(self, action, zindex=None, layer=None):
        if action == 'add':
            layerapi = LayerAPI(self._parent, layer)
            layerapi.layer_stopped.connect(self._layer_stopped)
            self._layers.append(layerapi)

        self.PropertiesChanged('org.chemlab.UChroma.AnimationManager',
                               {'CurrentRenderers': self.CurrentRenderers}, [])

    def _state_changed(self, state):
        self._state = state
        self._logger.debug("_state_changed: %s", state)
        self.PropertiesChanged('org.chemlab.UChroma.AnimationManager',
                               {'AnimationState': self.AnimationState}, [])


    @property
    def CurrentRenderers(self) -> tuple:
        return tuple([(x.layer_type, x.layer_path) \
            for x in sorted(self._layers, key=lambda z: z.layer_zindex)])


    @property
    def AvailableRenderers(self) -> dict:
        avail = {}
        infos = self._animgr.renderer_info

        for key, info in infos.items():
            avail[key] = dbus_prepare({'meta': info.meta, 'traits': info.traits})[0]

        return avail


    def AddRenderer(self, name: str, zindex: int, traits: dict) -> str:
        self._logger.debug('AddRenderer: name=%s zindex=%d traits=%s',
                           name, zindex, traits)
        if zindex < 0:
            zindex = None

        z = self._animgr.add_renderer(name, traits=traits, zindex=zindex)
        if z >= 0:
            return LayerAPI.get_layer_path(self._path, z)
        return None


    def RemoveRenderer(self, zindex: int) -> bool:
        return self._animgr.remove_renderer(zindex)


    def StopAnimation(self):
        return self._animgr.stop()


    def PauseAnimation(self):
        return self._animgr.pause()


    @property
    def AnimationState(self):
        return self._state



class DeviceManagerAPI:
    """
    <node>
        <interface name='org.chemlab.UChroma.DeviceManager'>
            <method name='GetDevices'>
                <arg direction='out' type='ao' />
            </method>

            <signal name='DevicesChanged'>
                <arg direction='out' type='s' name='action' />
                <arg direction='out' type='o' name='device' />
            </signal>
        </interface>
    </node>
    """

    def __init__(self, device_manager, logger):
        self._dm = device_manager
        self._logger = logger
        self._bus = None
        self._dm.callbacks.append(self._dm_callback)
        self._devs = OrderedDict()


    def GetDevices(self):
        """
        Get the list of object paths associated with discovered devices
        """
        if self._dm.devices is None:
            return []
        return tuple([x.bus_path for x in self._devs.values()])


    DevicesChanged = signal()


    def _publish_device(self, device):
        devapi = DeviceAPI(device, self._bus)
        devapi.publish()

        self._devs[device.key] = devapi

        return devapi.bus_path


    def _unpublish_device(self, device):
        devapi = self._devs.pop(device.key, None)
        if devapi is not None:
            devapi.unpublish()
            return devapi.bus_path

        return None


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
            self.DevicesChanged(action, path)


    def run(self):
        """
        Publish the service
        """
        self._bus = SessionBus()
        self._bus.publish('org.chemlab.UChroma', self)

