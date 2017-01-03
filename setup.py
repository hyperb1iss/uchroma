import re
import sys

from pydoc import locate

from setuptools import setup
from setuptools.command.install import install


RAZER_VENDOR_ID = 0x1532


__version__ = re.search(
    r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
    open('uchroma/__init__.py').read()).group(1)



class GenerateHWDB(install):
    def generate_hwdb(self):
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
        print(self.generate_hwdb())


setup(name='uchroma',
      version=__version__,
      description='Color control for Razer Chroma peripherals',
      url='https://github.com/cyanogen/uchroma',
      author='Steve Kondik',
      author_email='shade@chemlab.org',
      license='LGPL',
      packages=['uchroma'],
      scripts=['scripts/uchroma'],
      install_requires=['grapefruit', 'hidapi', 'numpy'],
      cmdclass={'hwdb': GenerateHWDB},
      zip_safe=False)
