from enum import Enum


RAZER_VENDOR_ID = 0x1532


class Model(Enum):
    """
    Enumeration of all models supported by uChroma

    This enumeration is used for device discovery as well
    as detection, and is parsed into a set of HWDB entries
    at build time.
    """
    KEYBOARD = {
        0x010D: 'BlackWidow Ultimate 2012',
        0x011A: 'BlackWidow Ultimate 2013',
        0x011B: 'BlackWidow Classic',
        0x0203: 'BlackWidow Chroma',
        0x0208: 'Tartarus Chroma',
        0x0209: 'BlackWidow Chroma Tournament Edition',
        0x0214: 'BlackWidow Ultimate 2016',
        0x0216: 'BlackWidow X Chroma',
        0x021A: 'BlackWidow X Chroma Tournament Edition',
    }
    LAPTOP = {
        0x0205: 'Blade Stealth',
        0x0210: 'Blade Pro (Late 2016)',
        0x0220: 'Blade Stealth (Late 2016)'
    }
    MOUSE = {
        0x002F: 'Imperator 2012',
        0x0042: 'Abyssus 2014',
        0x0043: 'DeathAdder Chroma',
        0x0044: 'Mamba (Wired)',
        0x0045: 'Mamba (Wireless)',
        0x0046: 'Mamba Tournament Edition',
        0x0048: 'Orochi (Wired)'
    }
    MOUSEPAD = {
        0x0C00: 'Firefly'
    }

