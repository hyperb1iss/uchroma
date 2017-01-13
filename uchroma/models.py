from enum import Enum


RAZER_VENDOR_ID = 0x1532


class Model(object):
    """
    Device identifiers, quirks, and configuration.

    These enumerations are used for device discovery as well
    as detection, and is parsed into a set of HWDB entries
    at build time.

    Devices are organized by type, and must enumerate their
    USB product ID and display name.
    """

    class Keyboard(Enum):
        """
        Keyboards
        """
        BLACKWIDOW_ULTIMATE_2012 = (0x010D, 'BlackWidow Ultimate 2012')
        ANANSI = (0x010F, 'Anansi')
        BLACKWIDOW_ULTIMATE_2013 = (0x011A, 'BlackWidow Ultimate 2013')
        BLACKWIDOW_ORIGINAL = (0x011B, 'BlackWidow Classic')
        BLACKWIDOW_CHROMA = (0x0203, 'BlackWidow Chroma')
        TARTARUS_CHROMA = (0x0208, 'Tartarus Chroma')
        BLACKWIDOW_CHROMA_TE = (0x0209, 'BlackWidow Chroma Tournament Edition')
        BLACKWIDOW_ULTIMATE_2016 = (0x0214, 'BlackWidow Ultimate 2016')
        BLACKWIDOW_X_CHROMA = (0x0216, 'BlackWidow X Chroma')
        BLACKWIDOW_X_CHROMA_TE = (0x021A, 'BlackWidow X Chroma Tournament Edition')
        ORNATA_CHROMA = (0x21e, 'Ornata Chroma')


    class Laptop(Enum):
        """
        Laptops
        """
        BLADE_STEALTH = (0x0205, 'Blade Stealth')
        BLADE_QHD = (0x020F, 'Blade Stealth (QHD)')
        BLADE_PRO_LATE_2016 = (0x0210, 'Blade Pro (Late 2016)')
        BLADE_STEALTH_LATE_2016 = (0x0220, 'Blade Stealth (Late 2016)')


    class Mouse(Enum):
        """
        Mice
        """
        IMPERATOR = (0x002F, 'Imperator 2012')
        ABYSSUS = (0x0042, 'Abyssus 2014')
        DEATHADDER_CHROMA = (0x0043, 'DeathAdder Chroma')
        MAMBA_WIRED = (0x0044, 'Mamba (Wired)')
        MAMBA_WIRELESS = (0x0045, 'Mamba (Wireless)')
        MAMBA_TE_WIRED = (0x0046, 'Mamba Tournament Edition')
        OROCHI_CHROMA = (0x0048, 'Orochi (Wired)')
        NAGA_HEX_V2 = (0x0050, 'Naga Hex V2')
        DEATHADDER_ELITE = (0x005C, 'DeathAdder Elite')


    class MousePad(Enum):
        """
        Mouse pads
        """
        FIREFLY = (0x0C00, 'Firefly')


    class Type(Enum):
        """
        All supported hardware types
        """
        KEYBOARD = 'Keyboard'
        LAPTOP = 'Laptop'
        MOUSE = 'Mouse'
        MOUSEPAD = 'MousePad'

        @property
        def device(self):
            return vars(Model)[self.value]


    def __init__(self, model: Enum):
        self._model = model


    @staticmethod
    def get(product_id: int) -> 'Model':
        """
        Get a Model instance by USB product ID

        :param product_id: The USB product ID
        :return: The Model
        """
        for model_type in Model.Type:
            for model in model_type.device:
                if model.value[0] == product_id:
                    return Model(model)

        return None


    @property
    def id(self) -> Enum:
        """
        The model enum
        """
        return self._model


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
        return self._model.value[0]


    @property
    def name(self) -> str:
        """
        The product name
        """
        return self._model.value[1]


    @property
    def type(self):
        """
        The hardware category
        """
        return Model.Type(self._model.__class__.__name__)


    @property
    def quirks(self):
        """
        Quirks applicable to this device

        Will be used to implement device-specific behaviors
        """
        quirks = []

        return quirks
