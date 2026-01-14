#
# uchroma - Copyright (C) 2021 Stefanie Kondik
#
# Minimal setup.py for Cython extension building.
# All other config is in pyproject.toml.
#
from setuptools import setup, Extension

import numpy as np

extensions = [
    Extension(
        'uchroma.server._crc',
        ['uchroma/server/_crc.pyx'],
        include_dirs=[np.get_include()],
    ),
    Extension(
        'uchroma._layer',
        ['uchroma/_layer.pyx'],
        include_dirs=[np.get_include()],
    ),
    Extension(
        'uchroma.fxlib._plasma',
        ['uchroma/fxlib/_plasma.pyx'],
        include_dirs=[np.get_include()],
        extra_compile_args=['-O3'],
    ),
]

for e in extensions:
    e.cython_directives = {'embedsignature': True}

setup(ext_modules=extensions)
