#
# uchroma - Copyright (C) 2017 Steve Kondik
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

# pylint: disable=protected-access, invalid-name

import re
import shutil
import sys

from abc import abstractmethod
from collections import OrderedDict
from typing import NamedTuple

from colr import Colr, color, strip_codes
from traitlets import Undefined
from argcomplete import autocomplete

from uchroma import __version__
from uchroma.color import ColorUtils, to_color
from uchroma.dbus_utils import dbus_prepare
from uchroma.traits import add_traits_to_argparse, apply_from_argparse, \
        dict_as_class_traits, HasTraits
from uchroma.util import ArgsDict, camel_to_snake, max_keylen

from .cmd import UChromaConsoleUtil


PYTHON_ARGCOMPLETE_OK = 1

ENTER = u'\033(0'
EXIT = u'\033(B'
CHAR_HORIZ = u'\x71'
CHAR_VERT = ENTER + u'\x78' + EXIT
CHAR_CROSS = u'\x6e'

RemoteTraits = NamedTuple('RemoteTraits', [('name', str),
                                           ('description', str),
                                           ('author', str),
                                           ('version', str),
                                           ('traits', HasTraits)])


def color_block(*values):
    output = Colr('')
    for value in values:
        col = to_color(value)
        output = output.center(9, text=col.html,
                               fore=ColorUtils.inverse(col).intTuple,
                               back=col.intTuple)
    return str(output)


class AbstractCommand(object):
    def __init__(self, parent):
        self._parent = parent
        self.width = shutil.get_terminal_size((80, 20)).columns - 5


    @property
    def driver(self):
        return self._parent.get_driver()


    @property
    def client(self):
        return self._parent._client


    def set_property(self, target, name, value):
        self._parent.set_property(target, name, value)


    def ellipsize(self, line: str, offset: int=0):
        if not isinstance(line, str):
            line = repr(line)

        length = self.width - 5 - offset
        if len(strip_codes(line)) < length:
            return line
        return '%s(...)' % line[:length]


    def columns(self, key_width, key, value):
        print(' %s %s %s' % (Colr(key).rjust(key_width), CHAR_VERT,
                             self.ellipsize(value, offset=key_width)))


    def seperator(self, key_width):
        print(' %s%s%s' % (ENTER + (CHAR_HORIZ * (key_width + 1)), \
                CHAR_CROSS, (CHAR_HORIZ * (self.width - key_width)) + EXIT))


    def show_traits(self, traits, values=None, indent=0):
        trait_data = traits.traits()

        if values is not None:
            trait_data = {k: v for k, v in trait_data.items() if k in values}

        count = v_count = 0
        s_traits = sorted(OrderedDict(trait_data).items())
        for name, trait in s_traits:
            if trait.get_metadata('config') is not True:
                continue

            value = None
            if values is not None:
                value = values.get(name)

            trait_type = re.sub(r'Trait$', '', trait.__class__.__name__).lower()
            desc = 'No description available'

            if trait_type == 'unicode':
                trait_type = 'string'

            if trait_type == 'caselessstrenum':
                trait_type = 'choice'
                desc = 'one of: %s' % ', '.join([x.lower() for x in sorted(trait.values)])
            elif hasattr(trait, 'info_text'):
                desc = trait.info_text

            constraints = []
            if hasattr(trait, 'min'):
                constraints.append('min: %s' % trait.min)
            if hasattr(trait, 'max'):
                constraints.append('max: %s' % trait.max)
            if hasattr(trait, '_minlen') and trait._minlen > 0:
                constraints.append('min length: %s' % trait._minlen)
            if hasattr(trait, '_maxlen') and trait._maxlen != sys.maxsize:
                constraints.append('max length: %s' % trait._maxlen)
            if hasattr(trait, 'default_value') and trait.default_value is not None \
                    and trait.default_value is not '' and trait.default_value is not Undefined:
                constraints.append('default: %s' % trait.default_value)

            constraint_str = ''
            if len(constraints) > 0:
                constraint_str = ', '.join(constraints)

            if count == 0:
                self.seperator(indent)

            if values is not None and len(values) > 0:
                if v_count > 0 and count > 0:
                    self.seperator(indent)
                v_count += 1

                if trait_type == 'color':
                    value = color_block(value)
                elif trait_type == 'colorscheme':
                    value = color_block(*value)

                self.columns(indent, color(name, style='bright'), value)
                self.columns(indent, '(%s)' % trait_type, desc)

                self.columns(indent, '', constraint_str)
            else:
                if len(constraint_str) > 0:
                    arginfo = ': '.join([trait_type, constraint_str])
                else:
                    arginfo = trait_type

                self.columns(indent, name, arginfo)

            count += 1


    def show_meta(self, trait_data, indent):
        meta = ArgsDict({k: v for k, v in trait_data._asdict().items() \
                if k not in 'traits'})
        if len(meta) < 3:
            return

        self.seperator(indent)

        for k, v in sorted(meta.items()):
            self.columns(indent, color(k, style='bright'), v)


    def list_objects(self, objects, values=None,
                     aliases=None, show_all: bool=False,
                     keylen=None):

        if aliases is None:
            keys = objects.keys()
        else:
            keys = [aliases.get(k, k) for k in objects.keys()]

        if keylen is None:
            keys = list(keys)
            for v in objects.values():
                keys.extend(v.traits.trait_names())
            if values is not None:
                for v in values.values():
                    keys.extend(v.keys())
            keylen = max_keylen(keys) + 1

        for name, trait_data in objects.items():
            if not show_all and values is not None and name not in values:
                continue

            dname = name
            if aliases is not None and name in aliases:
                dname = aliases[name]

            desc = trait_data.description

            vals = None
            if values is not None and name in values:
                vals = values[name]

            self.columns(keylen, color(dname, style='bright'),
                         color(desc, style='bright'))

            self.show_meta(trait_data, indent=keylen)

            self.show_traits(trait_data.traits, vals, indent=keylen)
            print('\n')


    def parse_traits(self, args):
        autocomplete(args.parser)
        trait_args, unparsed = args.parser.parse_known_args(args.unparsed, args)

        if not hasattr(trait_args, 'cmd_func'):
            args.parser.print_help()
            args.parser.exit(1)

        if hasattr(trait_args, 'traits'):
            trait_args.changed = apply_from_argparse(trait_args, traits=trait_args.traits)

        trait_args.unparsed = unparsed
        trait_args.cmd_func(trait_args)


    @classmethod
    def add_traits_parser(cls, parser, name, remote_traits, callback,
                          help_text: str=None, aliases=None):
        if help_text is None:
            help_text = remote_traits.description

        if aliases is None:
            aliases = []

        sub = parser.add_parser(name, help=help_text, aliases=aliases)
        add_traits_to_argparse(remote_traits.traits, sub)
        sub.set_defaults(cmd_func=callback, traits=remote_traits.traits, parser=sub)
        return sub


    @abstractmethod
    def add_parser(self, parser):
        pass


    @abstractmethod
    def parse(self, args):
        pass


class DumpCommand(AbstractCommand):
    def __init__(self, parent, dumpables):
        super(DumpCommand, self).__init__(parent)
        self._dumpables = dumpables


    def add_parser(self, sub):
        parser = sub.add_parser('dump', help='Dump device info')
        parser.add_argument("-w", "--wide", action="store_true",
                            help="Wide output (don't truncate long lines")
        parser.set_defaults(func=self.parse, parser=parser)
        return parser


    def parse(self, args):
        result = self.driver.GetAll('org.chemlab.UChroma.Device')
        keylen = max_keylen(result)
        props = OrderedDict(sorted({camel_to_snake(k): v for k, v in result.items()}.items()))

        for dumpable in self._dumpables:
            for v in dumpable.current_state.values():
                if len(v.keys()) == 0:
                    continue
                kk = max_keylen(v.keys())
                if kk > keylen:
                    keylen = kk

        print('\n Device properties:\n')

        device_index = "device-%s" % props.pop('device_index')
        device_name = props.pop('name')

        self.columns(keylen, color(device_index, style='bright'),
                     color(device_name, style='bright'))
        self.seperator(keylen)

        for k, v in props.items():
            self.columns(keylen, color(k, style='bright'), v)

        print('\n')

        for dumpable in self._dumpables:
            dumpable.dump(keylen=keylen)


class BrightnessCommand(AbstractCommand):

    def add_parser(self, sub):
        parser = sub.add_parser('brightness', help='Set/get brightness level')
        parser.add_argument('level', metavar='BRIGHTNESS', type=float, nargs='?',
                            help='Brightness level to set (0-100)')

        parser.set_defaults(func=self.parse, parser=parser)
        return parser


    def parse(self, args):
        if args.level is None:
            args.parser.exit(message='%f\n' % self.driver.Brightness)

        if args.level < 0 or args.level > 100:
            args.parser.error('Brightness must be between 0 and 100')

        self.driver.Brightness = args.level


class LEDCommand(AbstractCommand):
    def __init__(self, *args, **kwargs):
        super(LEDCommand, self).__init__(*args, **kwargs)
        self._leds = None


    def add_parser(self, sub):
        parser = sub.add_parser('led', help='Standalone LED control', add_help=False)
        parser.add_argument('-l', '--list', action='store_true',
                            help="Show available LEDs")
        parser.set_defaults(func=self.parse, parser=parser)
        return parser


    @property
    def available_leds(self):
        if self._leds is not None:
            return self._leds

        self._leds = OrderedDict()
        for name, t_dict in sorted(self.driver.AvailableLEDs.items()):
            traits = dict_as_class_traits(t_dict)
            self._leds[name] = RemoteTraits(name.lower(), \
                    "LED: %s" % name.title(), None, None, traits)

        return self._leds


    @property
    def current_state(self):
        state = OrderedDict()
        for led_name in self.available_leds:
            state[led_name] = OrderedDict(sorted(self.driver.GetLED(led_name).items()))
        return state


    def dump(self, keylen):
        if len(self.current_state) > 0:
            print("\n Current LED state:\n")
            self.list_objects(self.available_leds, self.current_state, keylen=keylen)


    def _list(self, args):
        print("\n Standalone LED control:\n")
        self.list_objects(self.available_leds, self.current_state, show_all=True)


    def parse(self, args):
        if args.list:
            self._list(args)
            args.parser.exit()

        sub = args.parser.add_subparsers(title="Subcommands", dest='led_cmd')

        lp = sub.add_parser('list')
        lp.set_defaults(cmd_func=self._list, parser=lp)

        # fill in args using traits
        for name, trait_data in self.available_leds.items():
            self.add_traits_parser(sub, name, trait_data, self._led_control)

        self.parse_traits(args)


    def _led_control(self, args):
        led = args.led_cmd.lower()

        if len(args.changed) == 0:
            args.parser.error("At least one option is required")

        if not self.driver.SetLED(led, dbus_prepare(args.changed, variant=True)[0]):
            args.parser.error("Failed to configure LED")


class FXCommand(AbstractCommand):
    def __init__(self, *args, **kwargs):
        super(FXCommand, self).__init__(*args, **kwargs)
        self._fx = None


    def add_parser(self, sub):
        parser = sub.add_parser('fx', help='Lighting and effects', add_help=False)
        parser.add_argument('-l', '--list', action='store_true',
                            help='List supported effects')
        parser.set_defaults(func=self.parse, parser=parser)
        return parser


    @property
    def available_fx(self):
        if self._fx is not None:
            return self._fx

        self._fx = OrderedDict()
        for name, t_dict in sorted(self.driver.AvailableFX.items()):
            traits = dict_as_class_traits(t_dict)
            if hasattr(traits, 'hidden') and traits.hidden:
                continue

            self._fx[name] = RemoteTraits(name, \
                traits.description, None, None, traits)

        return self._fx


    @property
    def current_state(self) -> dict:
        name, props = self.driver.CurrentFX
        return {name: OrderedDict(sorted(props.items()))}


    def dump(self, keylen):
        if len(self.current_state) > 0:
            if len(self.current_state) == 1 and \
                    list(self.current_state.keys())[0] in ('disable', 'custom_frame'):
                return
            print("\n Current built-in FX state:\n")
            self.list_objects(self.available_fx, self.current_state, keylen=keylen)


    def _list(self, args):
        print('\n Built-in effects and arguments:\n')
        self.list_objects(self.available_fx, self.current_state, show_all=True)


    def parse(self, args):
        if args.list:
            self._list(args)
            args.parser.exit(0)

        sub = args.parser.add_subparsers(title="Subcommands", dest='fx_cmd')

        # and a "list" subcommand (same as --list)
        ll = sub.add_parser('list')
        ll.set_defaults(cmd_func=self._list, parser=ll)

        # turn all traits into argparse commands
        for name, trait_data in self.available_fx.items():
            self.add_traits_parser(sub, name, trait_data, self._activate_fx)

        self.parse_traits(args)


    def _activate_fx(self, args):
        fx = args.fx_cmd.lower()
        if not self.driver.SetFX(fx, dbus_prepare(args.changed, variant=True)[0]):
            args.parser.error("Failed to activate effect")


class AnimationCommand(AbstractCommand):
    def __init__(self, *args, **kwargs):
        super(AnimationCommand, self).__init__(*args, **kwargs)
        self._renderer_info = None
        self._aliases = {}


    def add_parser(self, sub):
        parser = sub.add_parser('anim', help='Animation control', add_help=False)
        parser.add_argument('-l', '--list', action='store_true',
                            help="List available renderers and options")
        parser.set_defaults(func=self.parse, parser=parser)
        return parser


    def parse(self, args):
        if args.list:
            self._list(args)
            args.parser.exit(0)

        sub = args.parser.add_subparsers(title="Subcommands", dest='anim_sub')

        ll = sub.add_parser('list')
        ll.set_defaults(func_anim=self._list, parser=ll)

        add = sub.add_parser('add', help="Add a new animation layer", add_help=False)
        add.set_defaults(func_anim=self._add, parser=add)

        delete = sub.add_parser('delete', help="Delete a layer from the stack",
                                aliases=['del'], add_help=False)
        delete.set_defaults(func_anim=self._delete, parser=delete)

        modify = sub.add_parser('modify', help="Modify an existing layer",
                                aliases=['mod'], add_help=False)
        modify.set_defaults(func_anim=self._modify, parser=modify)

        pause = sub.add_parser('pause', help="Toggle pause state of the animation")
        pause.set_defaults(func_anim=self._pause, parser=pause)

        stop = sub.add_parser('stop', help="Stop and clear all renderers")
        stop.set_defaults(func_anim=self._stop, parser=stop)

        autocomplete(args.parser)
        anim_args, unparsed = args.parser.parse_known_args(args.unparsed, args)

        if not hasattr(anim_args, 'func_anim'):
            args.parser.print_help()
            args.parser.exit(1)

        anim_args.unparsed = unparsed
        anim_args.func_anim(anim_args)


    @property
    def renderer_info(self):
        if self._renderer_info is not None:
            return self._renderer_info

        avail = self.driver.AvailableRenderers
        if avail is None or len(avail) == 0:
            return None

        sar = OrderedDict(sorted(avail.items(),
                                 key=lambda k_v: k_v[1]['meta']['display_name']))
        exploded = OrderedDict()
        for name, t_anim in sar.items():
            meta = t_anim['meta']
            rt = RemoteTraits(meta['display_name'],
                              meta['description'],
                              meta['author'],
                              meta['version'],
                              dict_as_class_traits(t_anim['traits']))
            exploded[name] = rt
            self._aliases[name] = rt.name.replace(' ', '_').lower()

        self._renderer_info = exploded
        return self._renderer_info


    @property
    def current_state(self) -> dict:
        layers = OrderedDict()
        if hasattr(self.driver, 'CurrentRenderers'):
            num_renderers = len(self.driver.CurrentRenderers)
            if num_renderers > 0:
                for layer_idx in range(0, num_renderers):
                    layer = self.client.get_layer(self.driver, layer_idx)
                    props = layer.GetAll('org.chemlab.UChroma.Layer')
                    layers[props['Key']] = ArgsDict(sorted({camel_to_snake(k): v \
                            for k, v in props.items()}.items()))

        return layers


    def dump(self, keylen):
        if len(self.current_state) > 0:
            print("\n Current animation renderer state:\n")
            self.list_objects(self.renderer_info, self.current_state,
                              aliases=self._aliases, keylen=keylen)


    def _list(self, args):
        print('\n Available renderers and arguments:\n')
        self.list_objects(self.renderer_info, values=self.current_state,
                          aliases=self._aliases, show_all=True)


    def _pause(self, args):
        paused = self.driver.PauseAnimation()
        args.parser.exit(message="Pause state: %s\n" % paused)


    def _stop(self, args):
        if not self.driver.StopAnimation():
            args.parser.error("Failed to stop animation")


    def _add_renderer(self, args):
        rname = args.renderer
        if rname not in self.renderer_info:
            rname = {v: k for k, v in self._aliases.items()}[rname]

        zindex = -1
        if hasattr(args, 'zzz') and args.zzz is not None:
            zindex = args.zzz

        layer = self.driver.AddRenderer(rname, zindex, dbus_prepare(args.changed, variant=True)[0])
        if layer is None:
            args.parser.error("Failed to create renderer")

        args.parser.exit(message="Created layer: %s\n" % layer)


    def _add(self, args):
        layers = self.driver.CurrentRenderers
        args.parser.add_argument('-z', '--zindex', type=int, choices=range(0, len(layers) + 1),
                                 help="Z-index for the layer", dest='zzz')

        args, args.unparsed = args.parser.parse_known_args(args.unparsed, args)

        sub = args.parser.add_subparsers(title="Animation renderers", dest='renderer')

        for name, trait_data in self.renderer_info.items():
            alias = []
            if name in self._aliases:
                alias.append(name)
                name = self._aliases[name]

            self.add_traits_parser(sub, name, trait_data, self._add_renderer, aliases=alias)

        self.parse_traits(args)


    def _modify_layer(self, args):
        layer = int(args.layer)

        if len(args.changed) == 0:
            args.parser.error("No modifications were specified, try --help")

        layer_obj = self.client.get_layer(self.driver, layer)

        # Renderers expose their properties via dbus while running
        for k, v in args.changed.items():
            self.set_property(layer_obj, k, v)

        args.parser.exit(message="Layer %d updated\n" % layer)


    def _modify(self, args):
        layers = self.driver.CurrentRenderers
        if layers is None or len(layers) == 0:
            args.parser.error("No animation layers are active")

        sub = args.parser.add_subparsers(title="Active animation layers", dest='layer')

        for layer_idx in range(0, len(layers)):
            renderer = self.renderer_info[layers[layer_idx][0]]
            self.add_traits_parser(sub, str(layer_idx), renderer, self._modify_layer, \
                help_text="Layer %d: %s" % (layer_idx, renderer.description))

        self.parse_traits(args)


    def _delete(self, args):
        layers = self.driver.CurrentRenderers
        if layers is None or len(layers) == 0:
            args.parser.error("No animation layers are active")

        args.parser.add_argument('zindex', type=int, choices=range(0, len(layers)),
                                 help="Layer index to be removed")

        delete_args = args.parser.parse_args(args.unparsed, args)

        if not self.driver.RemoveRenderer(delete_args.zindex):
            args.parser.error("Failed to delete layer")

        args.parser.exit(message="Layer %d deleted\n" % delete_args.zindex)



class UChromaTool(UChromaConsoleUtil):

    def _add_subparsers(self, sub):
        super()._add_subparsers(sub)

        driver = self.get_driver()
        cmds = []

        if hasattr(driver, 'Brightness'):
            cmds.append(BrightnessCommand(self))

        if hasattr(driver, 'AvailableLEDs'):
            cmds.append(LEDCommand(self))

        if hasattr(driver, 'AvailableFX'):
            cmds.append(FXCommand(self))

        if hasattr(driver, 'AvailableRenderers'):
            cmds.append(AnimationCommand(self))

        dumpables = []
        for cmd in cmds:
            if hasattr(cmd, 'dump'):
                dumpables.append(cmd)

        cmds.append(DumpCommand(self, dumpables))

        for cmd in cmds:
            cmd.add_parser(sub)


def run_client():
    UChromaTool().run()


if __name__ == '__main__':
    run_client()
