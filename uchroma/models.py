from collections import namedtuple
from enum import Enum, IntEnum

from uchroma.fixups import BLADE_PRO_KEY_ALIGNMENT_MAP

from uchroma.types import FX


RAZER_VENDOR_ID = 0x1532


class Quirks(IntEnum):
    """
    Various "quirks" that are found across hardware models.
    """

    # Always use transaction code 0x3F
    TRANSACTION_CODE_3F = 1

    # Use "extended" commands
    EXTENDED_FX_CMDS = 2

    # Control device brightness with the scroll wheel LED
    SCROLL_WHEEL_BRIGHTNESS = 3

    # Device has charge and dock controls
    WIRELESS = 4

    # Needs transaction code 0x80 for custom frame data
    CUSTOM_FRAME_80 = 5

    # Control device brightness with the logo LED
    LOGO_LED_BRIGHTNESS = 6

    # Device has individual "profile" LEDs
    PROFILE_LEDS = 7

    # Device only supports spectrum effect on the backlight LED
    BACKLIGHT_LED_FX_ONLY = 8


_H = namedtuple('_H',
                ['product_id', 'product_name', 'matrix_dims', 'quirks', 'fixup_args'])
_H.__new__.__defaults__ = (None,) * len(_H._fields)


class HardwareInfo(_H, Enum):

    @property
    def has_matrix(self) -> bool:
        """
        True if the device has an addressable key matrix
        """
        return self.matrix_dims is not None


    def has_quirk(self, *quirks) -> bool:
        """
        True if quirk is required for the device

        :param quirks The quirks to check (varargs)

        :return: True if the quirk is required
        """
        if self.quirks is None:
            return False

        for quirk in quirks:
            if isinstance(self.quirks, (list, tuple)) and quirk in self.quirks:
                return True
            if self.quirks == quirk:
                return True

        return False


    @property
    def type(cls):
        return Hardware.Type[cls.__class__.__name__.upper()]



class Headset(HardwareInfo):
    """
    Headsets
    """
    KRAKEN = (0x0504, 'Kraken 7.1 (Rainie)')
    KRAKEN_V2 = (0x0510, 'Kraken 7.1 V2 (Kylie)')

    @property
    def supported_fx(self) -> tuple:
        return (FX.DISABLE, FX.BREATHE, FX.SPECTRUM, FX.STATIC)


class BaseKeyboard(HardwareInfo):

    @property
    def supported_fx(self) -> tuple:
        fx = [FX.DISABLE, FX.WAVE, FX.REACTIVE, FX.BREATHE,
              FX.SPECTRUM, FX.STATIC, FX.STARLIGHT]

        if self.has_matrix:
            fx.extend([FX.CUSTOM_FRAME, FX.RAINBOW, FX.ALIGNMENT])

        return tuple(fx)


class Keyboard(BaseKeyboard):
    """
    Keyboards
    """
    BLACKWIDOW_ULTIMATE_2012 = \
        _H(0x010D, 'BlackWidow Ultimate 2012', (6, 22),
           quirks=(Quirks.LOGO_LED_BRIGHTNESS))
    ANANSI = \
        _H(0x010F, 'Anansi',
           quirks=(Quirks.BACKLIGHT_LED_FX_ONLY))
    BLACKWIDOW_ULTIMATE_2013 = \
        _H(0x011A, 'BlackWidow Ultimate 2013', (6, 22),
           quirks=(Quirks.LOGO_LED_BRIGHTNESS))
    BLACKWIDOW_ORIGINAL = \
        _H(0x011B, 'BlackWidow Classic', (6, 22),
           quirks=(Quirks.LOGO_LED_BRIGHTNESS))
    BLACKWIDOW_CHROMA = \
        _H(0x0203, 'BlackWidow Chroma', (6, 22))
    TARTARUS_CHROMA = \
        _H(0x0208, 'Tartarus Chroma',
           quirks=(Quirks.PROFILE_LEDS))
    BLACKWIDOW_CHROMA_TE = \
        _H(0x0209, 'BlackWidow Chroma Tournament Edition', (6, 22))
    BLACKWIDOW_ULTIMATE_2016 = \
        _H(0x0214, 'BlackWidow Ultimate 2016', (6, 22))
    BLACKWIDOW_X_CHROMA = \
        _H(0x0216, 'BlackWidow X Chroma', (6, 22))
    BLACKWIDOW_X_CHROMA_TE = \
        _H(0x021A, 'BlackWidow X Chroma Tournament Edition', (6, 22))
    ORNATA_CHROMA = \
        _H(0x21e, 'Ornata Chroma', (6, 22),
           quirks=(Quirks.EXTENDED_FX_CMDS))



class Laptop(BaseKeyboard):
    """
    Laptops
    """
    BLADE_STEALTH = \
        _H(0x0205, 'Blade Stealth', (6, 22))
    BLADE_QHD = \
        _H(0x020F, 'Blade Stealth (QHD)', (6, 22))
    BLADE_PRO_LATE_2016 = \
        _H(0x0210, 'Blade Pro (Late 2016)', (6, 25),
           fixup_args={'alignment_map': BLADE_PRO_KEY_ALIGNMENT_MAP})
    BLADE_STEALTH_LATE_2016 = \
        _H(0x0220, 'Blade Stealth (Late 2016)', (6, 25))

    def has_quirk(self, *quirks) -> bool:
        if Quirks.CUSTOM_FRAME_80 in quirks:
            return True

        return super().has_quirk(*quirks)


    @property
    def supported_fx(self) -> tuple:
        fx = list(super().supported_fx)
        fx.extend([FX.GRADIENT, FX.SWEEP, FX.CIRCLE, FX.HIGHLIGHT, FX.MORPH, FX.FIRE,
                   FX.RIPPLE_SOLID, FX.RIPPLE, FX.SPECTRUM_BLADE])
        return tuple(fx)


class Mouse(HardwareInfo):
    """
    Mice
    """
    IMPERATOR = \
        _H(0x002F, 'Imperator 2012')
    ABYSSUS = \
        _H(0x0042, 'Abyssus 2014')
    DEATHADDER_CHROMA = \
        _H(0x0043, 'DeathAdder Chroma')
    MAMBA_WIRED = \
        _H(0x0044, 'Mamba (Wired)', (1, 15))
    MAMBA_WIRELESS = \
        _H(0x0045, 'Mamba (Wireless)', (1, 15),
           quirks=(Quirks.WIRELESS))
    MAMBA_TE_WIRED = \
        _H(0x0046, 'Mamba Tournament Edition', (1, 16))
    OROCHI_CHROMA = \
        _H(0x0048, 'Orochi (Wired)',
           quirks=(Quirks.SCROLL_WHEEL_BRIGHTNESS))
    NAGA_HEX_V2 = \
        _H(0x0050, 'Naga Hex V2',
           quirks=(Quirks.EXTENDED_FX_CMDS, Quirks.TRANSACTION_CODE_3F))
    DEATHADDER_ELITE = \
        _H(0x005C, 'DeathAdder Elite',
           quirks=(Quirks.TRANSACTION_CODE_3F))


    @property
    def supported_fx(self):
        fx = [FX.DISABLE, FX.WAVE, FX.REACTIVE, FX.BREATHE, FX.SPECTRUM, FX.STATIC]
        if self.has_matrix:
            fx.extend([FX.CUSTOM_FRAME])

        return tuple(fx)


class MousePad(HardwareInfo):
    """
    Mouse pads
    """
    FIREFLY = \
        _H(0x0C00, 'Firefly')


    @property
    def supported_fx(self):
        return (FX.DISABLE, FX.WAVE, FX.SPECTRUM, FX.STATIC)



class Hardware(object):
    """
    Device identifiers, quirks, and configuration.

    These enumerations are used for device discovery as well
    as detection, and is parsed into a set of HWDB entries
    at build time.

    Devices are organized by type, and must enumerate their
    USB product ID and display name.
    """
    class Type(Enum):
        """
        All supported hardware types
        """
        HEADSET = Headset
        KEYBOARD = Keyboard
        LAPTOP = Laptop
        MOUSE = Mouse
        MOUSEPAD = MousePad


    @staticmethod
    def get(product_id: int) -> HardwareInfo:
        """
        Get a HardwareInfo instance by USB product ID

        :param product_id: The USB product ID
        :return: The HardwareInfo
        """
        for hw_type in Hardware.Type:
            for hw in hw_type.value:
                if hw.value.product_id == product_id:
                    return hw

        return None
