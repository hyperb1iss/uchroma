import os
import re

from pydoc import locate

from setuptools import setup
from setuptools.command.install import install


RAZER_VENDOR_ID = 0x1532


def get_version():
    module_init = 'uchroma/version.py'

    if not os.path.isfile(module_init):
        module_init = '../' + module_init
        if not os.path.isfile(module_init):
            raise ValueError('Unable to determine version!')

    return re.search(r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                     open(module_init).read()).group(1)



class HWDBGenerator(install):

    @staticmethod
    def generate():
        model = locate('uchroma.models.Model')
        assert model is not None

        hwdb = ""
        for model_type in model.Type:
            for mod in model_type.value:
                hwdb += ('uchroma:usb:v%04Xp%04X*\n'
                         ' UCHROMA_DEVICE=%s\n\n'
                         % (RAZER_VENDOR_ID, mod.value[0], model_type.name.lower()))

        return hwdb


    def run(self):
        print(HWDBGenerator.generate())


setup(name='uchroma',
      version=get_version(),
      description='Color control for Razer Chroma peripherals',
      url='https://github.com/cyanogen/uchroma',
      author='Steve Kondik',
      author_email='shade@chemlab.org',
      license='LGPL',
      packages=['uchroma'],
      scripts=['scripts/uchroma'],
      install_requires=['grapefruit', 'hidapi', 'numpy', 'pyudev'],
      cmdclass={'hwdb': HWDBGenerator},
      zip_safe=False)
