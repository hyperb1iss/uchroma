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
    if (isinstance(arg, tuple) or isinstance(arg, list)) and len(arg) >= 3:
        return Color.NewFromRgb(arg[0], arg[1], arg[2])
    if isinstance(arg, str):
        return Color.NewFromHtml(arg)

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
