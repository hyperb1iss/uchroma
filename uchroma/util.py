from decorator import decorator

from grapefruit import Color


def to_color(arg) -> Color:
    """
    Convert various color representations to grapefruit.Color

    Handles RGB triplets, hexcodes, and html color names.

    :return: The color
    """
    if arg is None:
        return None
    if isinstance(arg, Color):
        return arg
    if isinstance(arg, str):
        return Color.NewFromHtml(arg)
    if isinstance(arg, tuple) or isinstance(arg, list):
        if isinstance(arg[0], list) or isinstance(arg[0], tuple) \
                or isinstance(arg[0], str) or isinstance(arg[0], Color):
            return [to_color(item) for item in arg]
        if len(arg) >= 3:
            if isinstance(arg[0], int):
                return Color.NewFromRgb(arg[0] / 255.0, arg[1] / 255.0, arg[2] / 255.0)
            elif isinstance(arg[0], float):
                return Color.NewFromRgb(arg[0], arg[1], arg[2])

    raise TypeError('Unable to parse color from \'%s\' (%s)' % (arg, type(arg)))


def to_rgb(arg) -> tuple:
    """
    Convert various representations to RGB tuples

    :return: An RGB tuple
    """
    if arg is None:
        return (0, 0, 0)
    if isinstance(arg, Color):
        return arg.intTuple[:3]
    if isinstance(arg, str):
        return Color.NewFromHtml(arg).intTuple[:3]
    if isinstance(arg, tuple) or isinstance(arg, list):
        if isinstance(arg[0], list) or isinstance(arg[0], tuple) \
                or isinstance(arg[0], str) or isinstance(arg[0], Color):
            return [to_rgb(item) for item in arg]
        if len(arg) >= 3:
            if isinstance(arg[0], int):
                return tuple(arg[:3])
            elif isinstance(arg[0], float):
                return (255 * arg[0], 255 * arg[1], 255 * arg[2])

    raise TypeError('Unable to parse color from \'%s\' (%s)' % (arg, type(arg)))


def colorarg(*decls):
    """
    Decorator to parse various color representations

    Invokes to_color on any arguments listed in decls. This will cause
    the listed arguments to be resolved to grapefruit.Color objects from
    the various different representations that might be in use.

    Example:

    @colorarg('color1', 'color2')
    def frobizzle(self, speed, color1=None, color2=None)

    """
    @decorator
    def wrapper(func, *args, **kwargs):
        code = func.__code__
        names = code.co_varnames[:code.co_argcount]

        new_args = list(args)

        for argname in decls:
            pos = names.index(argname)
            if pos < len(args):
                new_args[pos] = to_color(args[pos])

        return func(*new_args, **kwargs)

    return wrapper


def scale_brightness(brightness, from_hw=False):
    if from_hw:
        if brightness < 0 or brightness > 255:
            raise ValueError('Integer brightness must be between 0 and 255')

        if brightness is None:
            return 0.0

        return round(float(brightness) * (100.0 / 255.0), 2)

    if brightness < 0.0 or brightness > 100.0:
        raise ValueError('Float brightness must be between 0 and 100')

    if brightness is None:
        return 0

    return int(round(brightness * (255.0 / 100.0)))
