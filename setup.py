import os
import re

from pydoc import locate

from setuptools import command, setup, Extension
from setuptools.command.install import install
from setuptools.dist import Distribution

RAZER_VENDOR_ID = 0x1532


# Make sure Cython is installed first
Distribution(dict(setup_requires=['cython>=0.24']))

from Cython.Distutils import build_ext
from Cython.Build import cythonize


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
        hw = locate('uchroma.server.Hardware')
        assert hw is not None

        hwdb = ""
        for hw_type in hw.Type:
            for model in hw.get_type(hw_type):
                hwdb += ('uchroma:usb:v%04Xp%04X*\n'
                         ' UCHROMA_DEVICE=%s\n\n'
                         % (model.vendor_id, model.product_id, model.type.name.lower()))

        return hwdb


    def run(self):
        print(HWDBGenerator.generate())


extensions = [
    Extension('uchroma.server._crc', ['uchroma/server/_crc.pyx'], include_dirs=['.']),
    Extension('uchroma._layer', ['uchroma/_layer.pyx'], include_dirs=['.']),
    Extension('uchroma.fxlib._plasma', ['uchroma/fxlib/_plasma.pyx'], include_dirs=['.'], extra_compile_args=['-O3'])]

setup(name='uchroma',
      version=get_version(),
      description='Color control for Razer Chroma peripherals',
      url='https://github.com/cyanogen/uchroma',
      author='Steve Kondik',
      author_email='shade@chemlab.org',
      license='LGPL',
      platform='Linux',
      packages=['uchroma', 'uchroma.fxlib', 'uchroma.client', 'uchroma.server'],
      ext_modules = cythonize(extensions),
      entry_points={
          'console_scripts': [
              'uchroma = uchroma.client.client:run_client',
              'uchromad = uchroma.server.server:run_server'
          ]
      },
      install_requires=['argcomplete', 'colorlog', 'colr', 'evdev',
                        'frozendict', 'gbulb', 'grapefruit', 'hidapi',
                        'hsluv', 'numpy', 'pydbus', 'pyudev', 'ruamel.yaml',
                        'scikit-image', 'traitlets', 'wrapt'],
      cmdclass={'hwdb': HWDBGenerator, 'build_ext': build_ext},
      keywords='razer chroma uchroma driver keyboard mouse',
      include_package_data=True,
      setup_requires=['setuptools>=18.0', 'pytest-runner'],
      tests_require=['pytest'],
      zip_safe=False,
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
