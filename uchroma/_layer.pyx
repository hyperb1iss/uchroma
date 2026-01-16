
# pylint: disable=invalid-name

import numpy as np
cimport numpy as np


def color_to_np(*colors):
    # tuple(color) returns RGB only, need to add alpha for RGBA matrix
    result = []
    for c in colors:
        rgb = tuple(c)
        # Handle alpha as property or method
        if hasattr(c, 'alpha'):
            alpha = c.alpha
            if callable(alpha):
                alpha = alpha()
        else:
            alpha = 1.0
        result.append((rgb[0], rgb[1], rgb[2], alpha))
    return np.array(result, dtype=np.float64)


# a few methods pulled from skimage-dev for blending support
# remove these when 1.9 is released

def coords_inside_image(rr, cc, shape, val=None):
    mask = (rr >= 0) & (rr < shape[0]) & (cc >= 0) & (cc < shape[1])
    if val is None:
        return rr[mask], cc[mask]
    else:
        return rr[mask], cc[mask], val[mask]


def set_color(img, coords, color, alpha=1):
    rr, cc = coords

    if img.ndim == 2:
        img = img[..., np.newaxis]

    color = np.array(color, ndmin=1, copy=False)

    if img.shape[-1] != color.shape[-1]:
        raise ValueError('Color shape ({}) must match last '
                         'image dimension ({}). color=({})'.format( \
                                 color.shape[0], img.shape[-1], color))

    if np.isscalar(alpha):
        alpha = np.ones_like(rr) * alpha

    rr, cc, alpha = coords_inside_image(rr, cc, img.shape, val=alpha)

    color = color * alpha[..., np.newaxis]

    if np.all(img[rr, cc] == 0):
        img[rr, cc] = color
    else:

        src_alpha = color[..., -1][..., np.newaxis]
        src_rgb = color[..., :-1]

        dst_alpha = img[rr, cc][..., -1][..., np.newaxis] * 0.75
        dst_rgb = img[rr, cc][..., :-1]

        out_alpha = src_alpha + dst_alpha * (1 - src_alpha)
        out_rgb = (src_rgb * src_alpha + dst_rgb *dst_alpha * (1- src_alpha)) / out_alpha

        img[rr, cc] = np.clip(np.hstack([out_rgb, out_alpha]), a_min=0, a_max=1)
