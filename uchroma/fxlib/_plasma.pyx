# pylint: disable=invalid-name

from libc.math cimport cos, sin, sqrt
from math import pi

import numpy as np
cimport numpy as np

def draw_plasma(double width, double height, np.ndarray matrix, double duration, gradient):
    cdef int row, col
    cdef double x, y, val, cx, cy, pos
    cdef double glen = float(len(gradient))

    for col in range(0, int(width)):
        for row in range(0, int(height)):
            y = float(row) / (height * (width / height))
            x = float(col) / width

            val = sin(2.0 * (x * sin(duration / 2.0) + y * cos(duration / 3.0)) + duration)
            cx = x * sin(duration / 5.0)
            cy = y * cos(duration / 3.0)
            val += sin(sqrt(20.0 * (cx * cx + cy * cy) + 1.0) + duration)

            pos = glen * ((1.0 + sin(pi * val)) / 2.0)
            matrix[row][col] = tuple(gradient[int(pos) - 1])
