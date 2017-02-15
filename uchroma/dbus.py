# pylint: disable=invalid-name, no-member, protected-access

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

from grapefruit import Color
from pydbus import SessionBus
from pydbus.generic import signal
from traitlets.utils.bunch import Bunch

from uchroma.dbus_utils import ArgSpec, DescriptorBuilder, VariantDict
from uchroma.input import InputQueue
from uchroma.traits import TraitsPropertiesMixin, trait_as_dict
from uchroma.util import camel_to_snake, ensure_future, snake_to_camel


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
                   'supported_leds': 'as',
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
            return value

        else:
            return super(DeviceAPI, self).__getattribute__(name)


    @staticmethod
    def _get_bus_path(driver):
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
                self.InputEvent(VariantDict(event._asdict()))


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
                self._input_queue.detach()
                self._input_task.cancel()
                self._input_queue = None

            self._signal_input = state


    @property
    def FrameDebugOpts(self) -> dict:
        return VariantDict(self._driver.frame_control.debug_opts)


    @property
    def bus_path(self):
        """
        The bus path of this device.
        """
        return DeviceAPI._get_bus_path(self)


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



class FXManagerAPI(object):
    """
        <node>
          <interface name='org.chemlab.UChroma.FXManager'>
            <method name='GetCurrentFX'>
              <arg direction='out' type='s' name='name' />
              <arg direction='out' type='a{sv}' name='args' />
            </method>

            <method name='HasFX'>
              <arg direction='in' type='s' name='name' />
              <arg direction='out' type='b' name='result' />
            </method>

            <method name='SetFX'>
              <arg direction='in' type='s' name='name' />
              <arg direction='in' type='a{sv}' name='args' />
              <arg direction='out' type='b' name='status' />
            </method>

            <signal name='FXChanged'>
              <arg direction='out' type='s' name='name' />
            </signal>

            <property name='AvailableFX' type='a{sa{sa{sv}}}' access='read' />
          </interface>
        </node>
    """

    def __init__(self, driver):
        self._driver = driver
        self._logger = driver.logger
        self._current_fx = None
        self._current_fx_args = OrderedDict()


    @property
    def AvailableFX(self):
        avail = {}
        user_args = self._driver.fx_manager.user_args

        for fx in self._driver.fx_manager.available_fx:
            args = user_args[fx]
            argsdict = {}
            for k, v in args.items():
                argsdict[k] = VariantDict(trait_as_dict(v))

            avail[fx] = argsdict

        return avail


    def HasFX(self, name: str) -> bool:
        return self._driver.has_fx(name)


    def GetCurrentFX(self):
        """
        Get the currently active FX and arguments
        """
        if self._current_fx is None:
            return ('disable', {})

        return (self._current_fx.lower(), self._current_fx_args)


    def SetFX(self, name: str, args: dict) -> bool:
        """
        Set the desired FX, with options as a dict.
        """
        if not self._driver.has_fx(name):
            return False

        if self._driver.fx_manager.activate(name, **args):
            self._current_fx = name
            self._current_fx_args = args
            self.FXChanged(name)
            return True

        return False


    FXChanged = signal()



class LayerAPI(TraitsPropertiesMixin, object):

    def __init__(self, layer, logger, *args, **kwargs):
        super(LayerAPI, self).__init__(*args, **kwargs)

        self._logger = logger
        self._delegate = layer
        self.__class__.dbus = self._get_descriptor()

        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug('Layer created: %s', self.__class__.dbus)


    def _get_descriptor(self):
        exclude = ('blend_mode', 'opacity')
        if self._delegate.zorder > 0:
            exclude = ('background_color',)

        builder = DescriptorBuilder(self._delegate, 'org.chemlab.UChroma.Layer', exclude)

        for k, v in self._delegate.meta._asdict().items():
            attrib = snake_to_camel(k)
            setattr(self, attrib, v)
            builder.add_property(attrib, 's')

        setattr(self, 'Key', '%s.%s' % (self._delegate.__module__,
                                        self._delegate.__class__.__name__))
        builder.add_property('Key', 's')

        return builder.with_user_args('GetUserArgs').build()


    def GetUserArgs(self):
        argsdict = {}
        traits = self._delegate.traits()
        for k, v in traits.items():
            argsdict[snake_to_camel(k)] = VariantDict(trait_as_dict(v))
        return argsdict


class AnimationManagerAPI(object):
    """
        <node>
          <interface name='org.chemlab.UChroma.AnimationManager'>
            <method name='AddRenderer'>
              <arg direction='in' type='s' name='name' />
              <arg direction='in' type='a{sv}' name='traits' />
              <arg direction='out' type='o' name='layer' />
            </method>

            <method name='ClearRenderers'>
              <arg direction='out' type='b' name='status' />
            </method>

            <method name='StartAnimation'>
              <arg direction='out' type='b' name='status' />
            </method>

            <method name='StopAnimation'>
              <arg direction='out' type='b' name='status' />
            </method>

            <property name='AvailableRenderers' type='a{sa{sa{sv}}}' access='read' />

            <property name='CurrentRenderers' type='ao' access='read'>
              <annotation name='org.freedesktop.DBus.Property.EmitsChangedSignal' value='true' />
            </property>

           <property name='AnimationRunning' type='b' access='read'>
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

        # manually notify, startup order isn't guaranteed
        with self._animgr.hold_trait_notifications():
            self._update_layers(Bunch(name='renderers', old=[], new=self._animgr.renderers,
                                      owner=self, type='change'))
            self._state_changed(Bunch(name='running', old=False, new=self._animgr.running,
                                      owner=self, type='change'))

        self._animgr.observe(self._update_layers, names=['renderers'])
        self._animgr.observe(self._state_changed, names=['running'])


    def _update_layers(self, change):
        self._logger.debug("Layers changed: %s", change)
        if len(change.new) == 0 and len(change.old) > 0:
            for layer in self._layers:
                layer.unregister()
        elif len(change.new) > len(change.old):
            layer = change.new[-1]
            with layer.hold_trait_notifications():
                layerapi = LayerAPI(layer, self._logger)
                path = self._layer_path(layer.zorder)
                self._layers.append(self._bus.register_object(path, layerapi, None))

        self.PropertiesChanged('org.chemlab.UChroma.AnimationManager',
                               {'CurrentRenderers': self.CurrentRenderers}, [])


    PropertiesChanged = signal()


    def _layer_path(self, z) -> str:
        return '%s/layer/%d' % (self._path, z)


    def _state_changed(self, change):
        self._logger.debug("State changed: %s", change)
        self.PropertiesChanged('org.chemlab.UChroma.AnimationManager',
                               {'AnimationRunning': self.AnimationRunning}, [])


    @property
    def CurrentRenderers(self) -> list:
        return [self._layer_path(layer.zorder) for layer in self._animgr.renderers]


    @property
    def AvailableRenderers(self) -> list:
        avail = {}
        infos = self._animgr.renderer_info

        for key, info in infos.items():
            argsdict = {}
            argsdict['meta'] = VariantDict(info.meta._asdict())
            for k, v in info.traits.items():
                argsdict[k] = VariantDict(trait_as_dict(v))
            avail[key] = argsdict

        return avail


    def AddRenderer(self, name: str, traits: dict) -> str:
        z = self._animgr.add_renderer(name, **traits)
        if z >= 0:
            return self._layer_path(z)
        return None


    def ClearRenderers(self):
        return self._animgr.clear_renderers()


    def StartAnimation(self):
        return self._animgr.start()


    def StopAnimation(self):
        return self._animgr.stop()


    @property
    def AnimationRunning(self):
        return self._animgr.running



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

    def __init__(self, device_manager):
        self._dm = device_manager
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

        path = DeviceAPI._get_bus_path(device)

        self._devs[path] = []
        self._devs[path].append(self._bus.register_object(path, devapi, None))

        if device.fx_manager is not None:
            self._devs[path].append(self._bus.register_object( \
                path, FXManagerAPI(device), None))

        if device.animation_manager is not None:
            self._devs[path].append(self._bus.register_object( \
                path, AnimationManagerAPI(device, self._bus, path), None))


    def _unpublish_device(self, device):
        path = DeviceAPI._get_bus_path(device)

        if path in self._devs:
            for obj in self._devs[path]:
                obj.unregister()
            self._devs.pop(path)


    @asyncio.coroutine
    def _dm_callback(self, action, device):

        if action == 'add':
            self._publish_device(device)

        elif action == 'remove':
            self._unpublish_device(device)

        else:
            return

        self.DevicesChanged(action, DeviceAPI._get_bus_path(device))


    def run(self):
        self._bus = SessionBus()
        self._bus.publish('org.chemlab.UChroma', self)

