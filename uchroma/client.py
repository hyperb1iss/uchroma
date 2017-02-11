# pylint: disable=invalid-name
import re

import pydbus


BASE_PATH = '/org/chemlab/UChroma'
SERVICE = 'org.chemlab.UChroma'


class UChromaClient(object):

    def __init__(self):
        self._bus = pydbus.SessionBus()


    def get_device_paths(self) -> list:
        dm = self._bus.get(SERVICE)
        return dm.GetDevices()


    def get_device(self, identifier):
        if identifier is None:
            return None

        use_key = False
        if isinstance(identifier, str):
            if identifier.startswith(BASE_PATH):
                return self._bus.get(SERVICE, identifier)

            if re.match(r'\w{4}:\w{4}.\d{2}', identifier):
                use_key = True
            elif re.match(r'\d+', identifier):
                identifier = int(identifier)
            else:
                return None

        for dev_path in self.get_device_paths():
            dev = self.get_device(dev_path)
            if use_key and identifier == dev.Key:
                return dev
            elif identifier == dev.DeviceIndex:
                return dev

        return None


    def get_layer(self, device, layer_idx):
        layers = device.CurrentRenderers
        if layer_idx >= len(layers):
            raise ValueError("Layer index out of range")

        return self._bus.get(SERVICE, layers[layer_idx])


if __name__ == '__main__':
    uclient = UChromaClient()
    for u_dev_path in uclient.get_device_paths():
        u_dev = uclient.get_device(u_dev_path)
        print('[%s]: %s (%s / %s)' % \
            (u_dev.Key, u_dev.Name, u_dev.SerialNumber, u_dev.FirmwareVersion))
