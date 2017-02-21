from collections import OrderedDict

import pytest

from frozendict import frozendict
from traitlets import HasTraits

from uchroma.traits import FrozenDict


class FrozenDictTest(HasTraits):
    popsicle = FrozenDict()

    def __init__(self, *args, **kwargs):
        super(FrozenDictTest, self).__init__(*args, **kwargs)


obj = FrozenDictTest()


def test_frozendict_init_write_once():
    odict = OrderedDict()
    odict['test'] = 'best value ever'

    obj.popsicle = odict

    assert isinstance(obj.popsicle, frozendict)

    assert obj.popsicle is not None
    assert 'test' in obj.popsicle
    assert obj.popsicle['test'] == 'best value ever'


def test_frozendict_is_not_writable():
    with pytest.raises(KeyError):
        obj.popsicle['test_write'] == 'should fail'


