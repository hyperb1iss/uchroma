from enum import Enum


RAZER_VENDOR_ID = 0x1532


class Hardware(Enum):
    """
    Base enumeration type
    """
    def __init__(self, product_id, product_name, matrix_dims=None):
        self._product_id = product_id
        self._product_name = product_name
        self._matrix_dims = matrix_dims

    @property
    def product_id(self) -> int:
        """
        The USB product id
        """
        return self._product_id

    @property
    def product_name(self) -> str:
        """
        The name of this product
        """
        return self._product_name

    @property
    def matrix_dims(self) -> bool:
        """
        Addressable key matrix matrix_dims. None if unsupported
        """
        return self._matrix_dims

    @property
    def has_matrix(self) -> bool:
        """
        True if the device has an addressable key matrix
        """
        return self.matrix_dims is not None


class Headset(Hardware):
    """
    Headsets
    """
    KRAKEN = (0x0504, 'Kraken 7.1 (Rainie)')
    KRAKEN_V2 = (0x0510, 'Kraken 7.1 V2 (Kylie)')


class Keyboard(Hardware):
    """
    Keyboards
    """
    BLACKWIDOW_ULTIMATE_2012 = (0x010D, 'BlackWidow Ultimate 2012', (6, 22))
    ANANSI = (0x010F, 'Anansi', None)
    BLACKWIDOW_ULTIMATE_2013 = (0x011A, 'BlackWidow Ultimate 2013', (6, 22))
    BLACKWIDOW_ORIGINAL = (0x011B, 'BlackWidow Classic', (6, 22))
    BLACKWIDOW_CHROMA = (0x0203, 'BlackWidow Chroma', (6, 22))
    TARTARUS_CHROMA = (0x0208, 'Tartarus Chroma', None)
    BLACKWIDOW_CHROMA_TE = (0x0209, 'BlackWidow Chroma Tournament Edition', (6, 22))
    BLACKWIDOW_ULTIMATE_2016 = (0x0214, 'BlackWidow Ultimate 2016', (6, 22))
    BLACKWIDOW_X_CHROMA = (0x0216, 'BlackWidow X Chroma', (6, 22))
    BLACKWIDOW_X_CHROMA_TE = (0x021A, 'BlackWidow X Chroma Tournament Edition', (6, 22))
    ORNATA_CHROMA = (0x21e, 'Ornata Chroma', (6, 22))


class Laptop(Hardware):
    """
    Laptops
    """
    BLADE_STEALTH = (0x0205, 'Blade Stealth', (6, 22))
    BLADE_QHD = (0x020F, 'Blade Stealth (QHD)', (6, 22))
    BLADE_PRO_LATE_2016 = (0x0210, 'Blade Pro (Late 2016)', (6, 25))
    BLADE_STEALTH_LATE_2016 = (0x0220, 'Blade Stealth (Late 2016)', (6, 25))


class Mouse(Hardware):
    """
    Mice
    """
    IMPERATOR = (0x002F, 'Imperator 2012', None)
    ABYSSUS = (0x0042, 'Abyssus 2014', None)
    DEATHADDER_CHROMA = (0x0043, 'DeathAdder Chroma', None)
    MAMBA_WIRED = (0x0044, 'Mamba (Wired)', (1, 15))
    MAMBA_WIRELESS = (0x0045, 'Mamba (Wireless)', (1, 15))
    MAMBA_TE_WIRED = (0x0046, 'Mamba Tournament Edition', (1, 16))
    OROCHI_CHROMA = (0x0048, 'Orochi (Wired)', None)
    NAGA_HEX_V2 = (0x0050, 'Naga Hex V2', None)
    DEATHADDER_ELITE = (0x005C, 'DeathAdder Elite', None)


class MousePad(Hardware):
    """
    Mouse pads
    """
    FIREFLY = (0x0C00, 'Firefly')


class Model(object):
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


    def __init__(self, hardware: Hardware):
        self._hardware = hardware


    @staticmethod
    def get(product_id: int) -> 'Model':
        """
        Get a Model instance by USB product ID

        :param product_id: The USB product ID
        :return: The Model
        """
        for model_type in Model.Type:
            for model in model_type.value:
                if model.value[0] == product_id:
                    return Model(model)

        return None


    @property
    def hardware(self) -> Enum:
        """
        The hardware enumeration
        """
        return self._hardware


    @property
    def vendor_id(self) -> int:
        """
        The USB vendor ID
        """
        return RAZER_VENDOR_ID


    @property
    def product_id(self) -> int:
        """
        The USB product ID
        """
        return self.hardware.product_id


    @property
    def name(self) -> str:
        """
        The product name
        """
        return self.hardware.product_name


    @property
    def type(self):
        """
        The hardware category
        """
        return Model.Type[self._hardware.__class__.__name__.upper()]


    @property
    def quirks(self):
        """
        Quirks applicable to this device

        Will be used to implement device-specific behaviors
        """
        quirks = []

        return quirks
