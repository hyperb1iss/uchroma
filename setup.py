import os
import re

from pydoc import locate

from setuptools import setup
from setuptools.command.install import install

from Cython.Build import cythonize

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
      platform='Linux',
      license='LGPL',
      packages=['uchroma', 'uchroma.fxlib'],
      ext_modules = cythonize('uchroma/crc.pyx'),
      entry_points={
          'console_scripts': [
              'uchroma = uchroma.client:run_client',
              'uchromad = uchroma.server:run_server'
          ]
      },
      install_requires=['argcomplete', 'colorlog', 'colr', 'evdev',
                        'frozendict', 'gbulb', 'grapefruit', 'hidapi',
                        'hsluv', 'numpy', 'pydbus', 'pyudev', 'ruamel.yaml',
                        'scikit-image', 'traitlets', 'wrapt'],
      cmdclass={'hwdb': HWDBGenerator},
      keywords='razer chroma uchroma driver keyboard mouse',
      include_package_data=True,
      setup_requires=['pytest-runner'],
      tests_require=['pytest'],
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Intended Audience :: End Users/Desktop',
          'Topic :: Software Development :: Build Tools',
          'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python :: 3 :: Only',
          'Topic :: System :: Hardware :: Hardware Drivers'
      ])
