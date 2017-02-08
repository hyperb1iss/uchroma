# pylint: disable=invalid-name, no-member, protected-access

"""
D-Bus interfaces

These interfaces are designed to exist as a separate layer
and do not contain recursive dependencies with the lower
layers. UI clients should be designed to use these interfaces
rather than interacting with the hardware directly.
"""

import asyncio

from collections import OrderedDict
from enum import Enum

from pydbus import SessionBus
from pydbus.generic import signal

from uchroma.dbus_utils import DescriptorBuilder, VariantDict
from uchroma.traits import TraitsPropertiesMixin
from uchroma.types import FX
from uchroma.util import camel_to_snake, snake_to_camel


def dict_clean(obj):
    for k, v in obj.items():
        if v is None:
            obj[k] = ''
    return obj


class DeviceAPI(object):
    """
    D-Bus API for device properties and common hardware features.
    """

    _PROPERTIES = {'bus_path': 'o',
                   'device_index': 'u',
                   'device_type': 's',
                   'driver_version': 's',
                   'firmware_version': 's',
                   'has_matrix': 'b',
                   'height': 'i',
                   'is_wireless': 'b',
                   'key': 's',
                   'manufacturer': 's',
                   'name': 's',
                   'product_id': 'u',
                   'revision': 'u',
                   'serial_number': 's',
                   'supported_leds': 'as',
                   'sys_path': 's',
                   'vendor_id': 'u',
                   'width': 'i',
                   'zones': 'as'}


    def __init__(self, driver):
        self._driver = driver
        self.__class__.dbus = self._get_descriptor()


    def __getattribute__(self, name):
        # Intercept everything and delegate to the device class by converting
        # names between the D-Bus conventions to Python conventions.
        prop_name = camel_to_snake(name)
        if prop_name in DeviceAPI._PROPERTIES and hasattr(self._driver, prop_name):
            value = getattr(self._driver, prop_name)
            if isinstance(value, Enum):
                return value.name.lower()
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


    def _get_descriptor(self):
        builder = DescriptorBuilder(self, 'org.chemlab.UChroma.Device')
        for name, sig in DeviceAPI._PROPERTIES.items():
            if hasattr(self._driver, name):
                builder.add_property(name, sig, False)

        if hasattr(self._driver, 'brightness'):
            builder.add_property('brightness', 'd', True)

        if hasattr(self._driver, 'suspend') and hasattr(self._driver, 'resume'):
            builder.add_property('suspended', 'b', True)

        return builder.build()



class FXManagerAPI(object):
    """
        <node>
          <interface name='org.chemlab.UChroma.FXManager'>
            <method name='GetCurrentFX'>
              <arg direction='out' type='s' name='name' />
              <arg direction='out' type='a{ss}' name='args' />
            </method>

            <method name='HasFX'>
              <arg direction='in' type='s' name='name' />
              <arg direction='out' type='b' name='result' />
            </method>

            <method name='SetFX'>
              <arg direction='in' type='s' name='name' />
              <arg direction='in' type='a{ss}' name='args' />
              <arg direction='out' type='b' name='status' />
            </method>

            <method name='GetFXList'>
              <arg direction='out' type='a{ss}' name='fx' />
            </method>

            <signal name='FXChanged'>
              <arg direction='out' type='s' name='name' />
            </signal>

            <property name='SupportedFX' type='a{ss}' access='read' />
          </interface>
        </node>
    """

    def __init__(self, driver):
        self._driver = driver
        self._current_fx = FX.DISABLE
        self._current_fx_args = OrderedDict()


    @property
    def SupportedFX(self):
        sfx = OrderedDict()
        for fx in self._driver.supported_fx:
            sfx[fx.name.lower()] = fx.description

        return sfx


    def HasFX(self, name: str) -> bool:
        return self._driver.has_fx(name)


    def GetCurrentFX(self):
        """
        Get the currently active FX and arguments
        """
        return (self._current_fx.name.lower(), self._current_fx_args)


    def SetFX(self, name: str, args: dict) -> bool:
        """
        Set the desired FX, with options as a dict.
        """
        name = name.lower()

        if not self._driver.has_fx(name):
            return False

        if hasattr(self._driver, name):
            fx = getattr(self._driver, name)
            if fx(**args):
                self._current_fx = name
                self._current_fx_args = args
                self.FXChanged(name)
                return True

        return False


    def GetFXList(self):
        """
        Get the list of all available FX
        """
        fx = OrderedDict()
        for sfx in self._driver.supported_fx:
            fx[sfx.name.lower()] = sfx.description
        return fx


    FXChanged = signal()



class LayerAPI(TraitsPropertiesMixin, object):

    def __init__(self, layer, *args, **kwargs):
        super(LayerAPI, self).__init__(*args, **kwargs)

        self._delegate = layer
        self.__class__.dbus = self._get_descriptor()

    def _get_descriptor(self):
        builder = DescriptorBuilder(self._delegate, 'org.chemlab.UChroma.Layer')
        return builder.with_user_args('GetUserArgs').build()


    def GetUserArgs(self):
        argsdict = {}
        user_args = self.get_user_args()
        for k, v in user_args.items():
            argsdict[snake_to_camel(k)] = VariantDict(v)
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

            <property name='AvailableRenderers' type='a{sa{ss}}' access='read' />

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
        self._animgr = driver.animation_manager
        self._animgr.observe(self._update_layers, names=['renderers'])
        self._animgr.observe(self._state_changed, names=['running'])
        self._layers = []


    def _update_layers(self, change):
        if len(change.new) == 0 and len(change.old) > 0:
            for layer in self._layers:
                layer.unregister()
        elif len(change.new) > len(change.old):
            layer = change.new[-1]
            with layer.hold_trait_notifications():
                layerapi = LayerAPI(layer)
                path = self._layer_path(layer.zorder)
                self._layers.append(self._bus.register_object(path, layerapi, None))

        self.PropertiesChanged('org.chemlab.UChroma.AnimationManager',
                               {'CurrentRenderers': self.CurrentRenderers}, [])


    PropertiesChanged = signal()


    def _layer_path(self, z) -> str:
        return '%s/layer/%d' % (self._path, z)


    def _state_changed(self, change):
        self.PropertiesChanged('org.chemlab.UChroma.AnimationManager',
                               {'AnimationRunning': self.AnimationRunning}, [])


    @property
    def CurrentRenderers(self) -> list:
        return [self._layer_path(layer.zorder) for layer in self._animgr.renderers]


    @property
    def AvailableRenderers(self) -> list:
        infos = self._animgr.renderer_info
        result = OrderedDict()
        for key, info in infos.items():
            result[key] = info.meta._asdict()

        return result


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

        if device.supported_fx is not None and len(device.supported_fx) > 0:
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
            self._devs.remove(path)


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

