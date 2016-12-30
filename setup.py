from setuptools import setup

setup(name='uchroma',
      version='0.99',
      description='Driver for Razer Chroma peripherals',
      url='https://github.com/cyanogen/uchroma',
      author='Steve Kondik',
      author_email='shade@chemlab.org',
      license='LGPL',
      packages=['uchroma'],
      scripts=['scripts/uchroma'],
      install_requires=['grapefruit'],
      zip_safe=False)
