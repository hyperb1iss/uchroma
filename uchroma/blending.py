#
# uchroma - Copyright (C) 2021 Stefanie Kondik
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#

# pylint: disable=line-too-long, no-member

from collections.abc import Callable

import numpy as np

# Copyright (c) 2016 Florian Roscheck
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# Modified from blend_modes.py, https://github.com/flrs/blend_modes


class BlendOp:
    @staticmethod
    def soft_light(img_in, img_layer):
        """
        Apply soft light blending mode of a layer on an image.

        Find more information on `Wikipedia <https://en.wikipedia.org/w/index.php?title=Blend_modes&oldid=747749280#Soft_Light>`__.
        """

        # The following code does this:
        #   multiply = img_in[:, :, :3]*img_layer[:, :, :3]
        #   screen = 1.0 - (1.0-img_in[:, :, :3])*(1.0-img_layer[:, :, :3])
        #   comp = (1.0 - img_in[:, :, :3]) * multiply + img_in[:, :, :3] * screen
        #   ratio_rs = np.reshape(np.repeat(ratio,3),comp.shape)
        #   img_out = comp*ratio_rs + img_in[:, :, :3] * (1.0-ratio_rs)

        return (1.0 - img_in[:, :, :3]) * img_in[:, :, :3] * img_layer[:, :, :3] + img_in[
            :, :, :3
        ] * (1.0 - (1.0 - img_in[:, :, :3]) * (1.0 - img_layer[:, :, :3]))

    @staticmethod
    def lighten_only(img_in, img_layer):
        """
        Apply lighten only blending mode of a layer on an image.

        Find more information on `Wikipedia <https://en.wikipedia.org/w/index.php?title=Blend_modes&oldid=747749280#Lighten_Only>`__.
        """
        return np.maximum(img_in[:, :, :3], img_layer[:, :, :3])

    @staticmethod
    def screen(img_in, img_layer):
        """
        Apply screen blending mode of a layer on an image.

        Find more information on `Wikipedia <https://en.wikipedia.org/w/index.php?title=Blend_modes&oldid=747749280#Screen>`__.
        """
        return 1.0 - (1.0 - img_in[:, :, :3]) * (1.0 - img_layer[:, :, :3])

    @staticmethod
    def dodge(img_in, img_layer):
        """
        Apply dodge blending mode of a layer on an image.

        Find more information on `Wikipedia <https://en.wikipedia.org/w/index.php?title=Blend_modes&oldid=747749280#Dodge_and_burn>`__.
        """
        return np.minimum(img_in[:, :, :3] / (1.0 - img_layer[:, :, :3]), 1.0)

    @staticmethod
    def addition(img_in, img_layer):
        """
        Apply addition blending mode of a layer on an image.
        """
        return img_in[:, :, :3] + img_layer[:, :, :3]

    @staticmethod
    def darken_only(img_in, img_layer):
        """
        Apply darken only blending mode of a layer on an image.
        """
        return np.minimum(img_in[:, :, :3], img_layer[:, :, :3])

    @staticmethod
    def multiply(img_in, img_layer):
        """
        Apply multiply blending mode of a layer on an image.
        """
        return np.clip(img_layer[:, :, :3] * img_in[:, :, :3], 0.0, 1.0)

    @staticmethod
    def hard_light(img_in, img_layer):
        """
        Apply hard light blending mode of a layer on an image.

        Find more information on `Wikipedia <https://en.wikipedia.org/w/index.php?title=Blend_modes&oldid=747749280#Hard_Light>`__.
        """
        comp = np.greater(img_layer[:, :, :3], 0.5) * np.minimum(
            1.0 - ((1.0 - img_in[:, :, :3]) * (1.0 - (img_layer[:, :, :3] - 0.5) * 2.0)), 1.0
        ) + np.logical_not(np.greater(img_layer[:, :, :3], 0.5)) * np.minimum(
            img_in[:, :, :3] * (img_layer[:, :, :3] * 2.0), 1.0
        )
        return comp

    @staticmethod
    def difference(img_in, img_layer):
        """
        Apply difference blending mode of a layer on an image.

        Find more information on `Wikipedia <https://en.wikipedia.org/w/index.php?title=Blend_modes&oldid=747749280#Difference>`__.
        """
        comp = img_in[:, :, :3] - img_layer[:, :, :3]
        comp[comp < 0.0] *= -1.0

        return comp

    @staticmethod
    def subtract(img_in, img_layer):
        """
        Apply subtract blending mode of a layer on an image.

        Find more information on `Wikipedia <https://en.wikipedia.org/w/index.php?title=Blend_modes&oldid=747749280#Subtract>`__.
        """
        return img_in[:, :, :3] - img_layer[:, :, :3]

    @staticmethod
    def grain_extract(img_in, img_layer):
        """
        Apply grain extract blending mode of a layer on an image.

        Find more information on the `KDE UserBase Wiki <https://userbase.kde.org/Krita/Manual/Blendingmodes#Grain_Extract>`__.
        """
        return np.clip(img_in[:, :, :3] - img_layer[:, :, :3] + 0.5, 0.0, 1.0)

    @staticmethod
    def grain_merge(img_in, img_layer):
        """
        Apply grain merge blending mode of a layer on an image.

        Find more information on the `KDE UserBase Wiki <https://userbase.kde.org/Krita/Manual/Blendingmodes#Grain_Merge>`__.
        """
        return np.clip(img_in[:, :, :3] + img_layer[:, :, :3] - 0.5, 0.0, 1.0)

    @staticmethod
    def divide(img_in, img_layer):
        """
        Apply divide blending mode of a layer on an image.

        Find more information on `Wikipedia <https://en.wikipedia.org/w/index.php?title=Blend_modes&oldid=747749280#Divide>`__.
        """
        return np.minimum(
            (256.0 / 255.0 * img_in[:, :, :3]) / (1.0 / 255.0 + img_layer[:, :, :3]), 1.0
        )

    @classmethod
    def get_modes(cls):
        return sorted([x for x in dir(cls) if not x.startswith("_") and x != "get_modes"])


def _compose_alpha(img_in, img_layer, opacity: float = 1.0):
    """
    Calculate alpha composition ratio between two images.
    """
    comp_alpha = np.minimum(img_in[:, :, 3], img_layer[:, :, 3]) * opacity
    new_alpha = img_in[:, :, 3] + (1.0 - img_in[:, :, 3]) * comp_alpha
    np.seterr(divide="ignore", invalid="ignore")
    ratio = comp_alpha / new_alpha
    ratio[np.isnan(ratio)] = 0.0
    return ratio


def blend(
    img_in: np.ndarray, img_layer: np.ndarray, blend_op: str | Callable | None, opacity: float = 1.0
):
    # sanity check of inputs
    assert img_in.dtype == np.float64, "Input variable img_in should be of numpy.float64 type."
    assert img_layer.dtype == np.float64, (
        "Input variable img_layer should be of numpy.float64 type."
    )
    assert img_in.shape[2] == 4, "Input variable img_in should be of shape [:, :,4]."
    assert img_layer.shape[2] == 4, "Input variable img_layer should be of shape [:, :,4]."
    assert 0.0 <= opacity <= 1.0, "Opacity needs to be between 0.0 and 1.0."

    ratio = _compose_alpha(img_in, img_layer, opacity)

    if blend_op is None:
        blend_op = BlendOp.screen
    elif isinstance(blend_op, str):
        if hasattr(BlendOp, blend_op):
            blend_op = getattr(BlendOp, blend_op)
        else:
            raise ValueError(f"Invalid blend mode: {blend_op}")

    comp = blend_op(img_in, img_layer)

    ratio_rs = np.reshape(np.repeat(ratio, 3), [comp.shape[0], comp.shape[1], comp.shape[2]])
    img_out = comp * ratio_rs + img_in[:, :, :3] * (1.0 - ratio_rs)
    img_out = np.nan_to_num(
        np.dstack((img_out, img_in[:, :, 3]))
    )  # add alpha channel and replace nans
    return img_out
