import os
import re

from pydoc import locate

from setuptools import setup
from setuptools.command.install import install


RAZER_VENDOR_ID = 0x1532


def get_version():
    module_init = 'uchroma/__init__.py'

    if not os.path.isfile(module_init):
        module_init = '../' + module_init
        if not os.path.isfile(module_init):
            raise ValueError('Unable to determine version!')

    return re.search(r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                     open(module_init).read()).group(1)



class HWDBGenerator(install):

    @staticmethod
    def generate():
        models = locate('uchroma.models.Model')
        assert models is not None

        hwdb = ""
        for model_type in models:
            for devid in model_type.value:
                hwdb += ('uchroma:usb:v%04xp%04x*\n'
                         ' UCHROMA_DEVICE=%s\n\n'
                         % (RAZER_VENDOR_ID, devid, model_type.name.lower()))

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
