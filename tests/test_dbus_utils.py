import sys

from enum import Enum

from gi.repository import GLib
from grapefruit import Color
from traitlets import Int
from uchroma.dbus_utils import dbus_prepare

class EnumTest(Enum):
    FIRST = 1
    SECOND = 2
    THIRD = 3

def test_primitives():
    assert dbus_prepare(23)[1] == 'n'
    assert dbus_prepare(65536)[1] == 'i'
    assert dbus_prepare(sys.maxsize)[1] == 'x'
    assert dbus_prepare(False)[1] == 'b'
    assert dbus_prepare(23.0)[1] == 'd'
    assert dbus_prepare('asdf')[1] == 's'

def test_special_types():
    obj, sig = dbus_prepare(Color.NewFromHtml('black'))
    assert obj == '#000000'
    assert sig == 's'

    obj, sig = dbus_prepare(Int(5))
    assert isinstance(obj, dict)
    assert sig == 'a{sv}'
    for value in obj.values():
        assert isinstance(value, GLib.Variant)

    obj, sig = dbus_prepare(EnumTest)
    assert isinstance(obj, tuple)
    assert sig == '(sss)'

def test_dicts():
    simple = {'first': 1, 'second': 2}
    obj, sig = dbus_prepare(simple)
    assert obj == simple
    assert sig == 'a{sn}'

    obj, sig = dbus_prepare(simple, variant=True)
    for value in obj.values():
        assert isinstance(value, GLib.Variant)
    assert sig == 'a{sv}'

    mixed = {'first': 'string here', 'second': 2, 'third': (2, 2)}
    obj, sig = dbus_prepare(mixed)
    for value in obj.values():
        assert isinstance(value, GLib.Variant)
    assert sig == 'a{sv}'

    nested = {'first': {'nested1': 1}, 'second': {'nested2': 2}}
    obj, sig = dbus_prepare(nested)
    assert obj == nested
    assert sig == 'a{sa{sn}}'

    nested['second']['nested2'] = 'blah'
    obj, sig = dbus_prepare(nested)
    print('obj=%s sig=%s' % (obj, sig))
    assert isinstance(obj, dict)
    assert isinstance(obj['first'], GLib.Variant)
    assert isinstance(obj['first']['nested1'], int)
    assert sig == 'a{sv}'
