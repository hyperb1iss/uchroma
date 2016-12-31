from setuptools import setup
import re

__version__ = re.search(
    r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
    open('uchroma/__init__.py').read()).group(1)


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
      zip_safe=False)
