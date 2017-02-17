import os

from uchroma.hardware import Hardware, KeyMapping, Point, PointList


def test_config_loaded():
    assert Hardware.get_device(0x210).product_id == 0x0210

def test_recursive_attribute():
    assert Hardware.get_device(0x210).vendor_id == 0x1532

def test_type_coercion():
    hw = Hardware.get_device(0x210)
    assert isinstance(hw.key_mapping, KeyMapping)

    space = hw.key_mapping['KEY_SPACE']
    assert isinstance(space, PointList)

    assert len(space) == 5

    prev = 0
    for coord in space:
        assert isinstance(coord, Point)
        assert coord.y == 5
        assert coord.x > prev
        prev = coord.x

def test_flatten_serialize_yaml(tmpdir):
    yaml_file = str(tmpdir.join('hardware.yaml'))

    orig = Hardware.get_device(0x210)

    # built-in yaml files are hierarchial, we must flatten
    orig.flatten().save_yaml(yaml_file)

    loaded = Hardware.load_yaml(yaml_file)

    for slot in orig.__slots__:
        print(slot)
        if slot in ('parent', '_children'):
            assert loaded.parent is None
            assert loaded._children is None
        else:
            assert getattr(orig, slot) == getattr(loaded, slot)

