# pylint: disable=invalid-name

"""
D-Bus interfaces

These interfaces are designed to exist as a separate layer
and do not contain recursive dependencies with the lower
layers. UI clients should be designed to use these interfaces
rather than interacting with the hardware directly.
"""

import asyncio
import logging
import os

from collections import OrderedDict
from enum import Enum

from pydbus import SessionBus
from pydbus.generic import signal

from grapefruit import Color

from uchroma.dbus_utils import ArgSpec, dbus_prepare, DescriptorBuilder
from uchroma.input import InputQueue
from uchroma.led import LEDType
from uchroma.traits import TraitsPropertiesMixin
from uchroma.util import camel_to_snake, ensure_future, snake_to_camel, Signal


def dev_mode_enabled():
    return os.environ.get('UCHROMA_DEV') is not None


class DeviceAPI(object):
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
                      'dpi': 'a(ii)',
                      'dock_charge_color': 's'}


    def __init__(self, driver):
        self._driver = driver
        self._logger = driver.logger
        self.__class__.dbus = self._get_descriptor()
        self._signal_input = False
        self._input_task = None
        self._input_queue = None

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
            if isinstance(value, (list, tuple)) and len(value) > 0 and isinstance(value[0], Enum):
                return [x.name.lower() for x in value]
            return value

        else:
            return super(DeviceAPI, self).__getattribute__(name)


    @staticmethod
    def get_bus_path(driver):
        """
        Get the bus path for all services related to this device.
        """
        return '/org/chemlab/UChroma/%s/%04x_%04x_%02d' % \
            (driver.device_type.value, driver.vendor_id,
             driver.product_id, driver.device_index)


    @asyncio.coroutine
    def _dev_mode_input(self):
        while self._signal_input:
            event = yield from self._input_queue.get_events()
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


    @property
    def bus_path(self):
        """
        The bus path of this device.
        """
        return DeviceAPI.get_bus_path(self)


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


class LEDManagerAPI(object):
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

    def __init__(self, driver):
        self._driver = driver
        self._logger = driver.logger
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


class FXManagerAPI(object):
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

    def __init__(self, driver):
        self._driver = driver
        self._fx_manager = driver.fx_manager
        self._logger = driver.logger

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


class LayerAPI(TraitsPropertiesMixin, object):

    def __init__(self, layer, bus, path, logger, *args, **kwargs):
        super(LayerAPI, self).__init__(*args, **kwargs)

        self._logger = logger
        self._delegate = layer
        self._bus = bus
        self._path = path

        self._zindex = layer.zindex
        self._handle = None

        self.__class__.dbus = None

        self.layer_stopped = Signal()

        if layer.running:
            self.register()

        self._delegate.observe(self._z_changed, names=['zindex'])
        self._delegate.observe(self._state_changed, names=['running'])

        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug('Layer node created: %s', self.__class__.dbus)


    def _z_changed(self, change):
        if change.old != change.new:
            self.register()


    def _state_changed(self, change):
        if change.old != change.new:
            if change.new:
                self.register()
            elif self._handle != None:
                self._logger.info("Layer stopped zindex=%d (%s)",
                                  self._zindex, self._delegate.meta)
                self.unregister()
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


    def register(self):
        self.unregister()

        self.__class__.dbus = self._get_descriptor()

        self._zindex = self._delegate.zindex
        self._handle = self._bus.register_object(self.layer_path, self, None)
        self._logger.info("Registered layer API: %s", self.layer_path)


    def unregister(self):
        if self._handle is not None:
            self._handle.unregister()
            self._handle = None
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


class AnimationManagerAPI(object):
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

    def __init__(self, driver, bus, path):
        assert driver.animation_manager is not None, 'Animations not supported for this device'
        self._driver = driver
        self._bus = bus
        self._path = path
        self._logger = driver.logger
        self._animgr = driver.animation_manager
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
            layerapi = LayerAPI(layer, self._bus, self._path, self._logger)
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



class DeviceManagerAPI(object):
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
        if self._dm.devices is None:
            return []
        return tuple(self._devs.keys())


    DevicesChanged = signal()


    def _publish_device(self, device):
        devapi = DeviceAPI(device)

        path = DeviceAPI.get_bus_path(device)

        self._devs[path] = []
        self._devs[path].append(self._bus.register_object(path, devapi, None))

        if hasattr(device, 'fx_manager') and device.fx_manager is not None:
            self._devs[path].append(self._bus.register_object( \
                path, FXManagerAPI(device), None))

        if hasattr(device, 'animation_manager') and device.animation_manager is not None:
            self._devs[path].append(self._bus.register_object( \
                path, AnimationManagerAPI(device, self._bus, path), None))

        if hasattr(device, 'led_manager') and device.led_manager is not None:
            self._devs[path].append(self._bus.register_object( \
                path, LEDManagerAPI(device), None))


    def _unpublish_device(self, device):
        path = DeviceAPI.get_bus_path(device)

        if path in self._devs:
            for obj in self._devs[path]:
                obj.unregister()
            self._devs.pop(path)


    @asyncio.coroutine
    def _dm_callback(self, action, device):
        self._logger.info('%s: %s', action, device)

        if action == 'add':
            self._publish_device(device)
            device.restore_prefs()

        elif action == 'remove':
            self._unpublish_device(device)

        else:
            return

        self.DevicesChanged(action, DeviceAPI.get_bus_path(device))


    def run(self):
        self._bus = SessionBus()
        self._bus.publish('org.chemlab.UChroma', self)

