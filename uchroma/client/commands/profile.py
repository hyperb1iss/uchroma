#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
"""
Profile command — save and load device presets.

Profiles store device state (brightness, effects, LEDs) and can be
restored quickly.
"""

import json
from argparse import ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

from uchroma.client.commands.base import Command
from uchroma.client.device_service import get_device_service

PROFILE_DIR = Path.home() / ".config" / "uchroma" / "profiles"


class ProfileCommand(Command):
    """Manage device presets/profiles."""

    name = "profile"
    help = "Save and load device presets"
    aliases: ClassVar[list[str]] = ["preset", "prof"]

    def configure_parser(self, parser: ArgumentParser) -> None:
        sub = parser.add_subparsers(dest="profile_cmd", metavar="COMMAND")

        # list - show saved profiles
        sub.add_parser("list", aliases=["ls"], help="list saved profiles")

        # save - save current state as profile
        save_p = sub.add_parser("save", help="save current device state as profile")
        save_p.add_argument("name", metavar="NAME", help="profile name")
        save_p.add_argument("-f", "--force", action="store_true", help="overwrite existing profile")

        # load - apply a saved profile
        load_p = sub.add_parser("load", aliases=["apply"], help="load a saved profile")
        load_p.add_argument("name", metavar="NAME", help="profile name to load")

        # show - show profile contents
        show_p = sub.add_parser("show", aliases=["cat"], help="show profile contents")
        show_p.add_argument("name", metavar="NAME", help="profile name")

        # delete - remove a profile
        del_p = sub.add_parser("delete", aliases=["rm", "remove"], help="delete a profile")
        del_p.add_argument("name", metavar="NAME", help="profile name to delete")

    def run(self, args: Namespace) -> int:
        cmd = getattr(args, "profile_cmd", None)

        if cmd is None or cmd in ("list", "ls"):
            return self._list(args)
        elif cmd == "save":
            return self._save(args)
        elif cmd in ("load", "apply"):
            return self._load(args)
        elif cmd in ("show", "cat"):
            return self._show(args)
        elif cmd in ("delete", "rm", "remove"):
            return self._delete(args)

        return 0

    # ─────────────────────────────────────────────────────────────────────────
    # List profiles
    # ─────────────────────────────────────────────────────────────────────────

    def _list(self, args: Namespace) -> int:
        """List all saved profiles."""
        self.print()
        self.print(self.out.header(" Saved Profiles:"))
        self.print()

        if not PROFILE_DIR.exists():
            self.print(self.out.muted("  No profiles saved yet"))
            self.print()
            self.print(
                self.out.muted(
                    f"  Save one with: {self.out.command('uchroma profile save <name>')}"
                )
            )
            self.print()
            return 0

        profiles = list(PROFILE_DIR.glob("*.json"))
        if not profiles:
            self.print(self.out.muted("  No profiles saved yet"))
            self.print()
            return 0

        key_width = 20

        for path in sorted(profiles):
            name = path.stem
            try:
                data = json.loads(path.read_text())
                device_name = data.get("device_name", "unknown")
                created = data.get("created", "")
                if created:
                    dt = datetime.fromisoformat(created)
                    created = dt.strftime("%Y-%m-%d %H:%M")

                self.print(
                    self.out.table_row(
                        key_width,
                        self.out.device(name),
                        f"{device_name} {self.out.muted(f'({created})')}",
                    )
                )
            except (json.JSONDecodeError, OSError):
                self.print(
                    self.out.table_row(
                        key_width, self.out.device(name), self.out.muted("(invalid)")
                    )
                )

        self.print()
        return 0

    # ─────────────────────────────────────────────────────────────────────────
    # Save profile
    # ─────────────────────────────────────────────────────────────────────────

    def _save(self, args: Namespace) -> int:
        """Save current device state as a profile."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        name = args.name
        path = PROFILE_DIR / f"{name}.json"

        if path.exists() and not args.force:
            self.print(self.out.error(f"Profile '{name}' already exists"))
            self.print(self.out.muted("  Use --force to overwrite"))
            return 1

        # Capture device state
        profile = self._capture_state(service, device)

        # Save
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(profile, indent=2))

        self.print(self.out.success(f"Saved profile: {name}"))
        self.print(self.out.muted(f"  {self.out.path(str(path))}"))
        return 0

    def _capture_state(self, service, device) -> dict[str, Any]:
        """Capture current device state as a profile dict."""
        profile: dict[str, Any] = {
            "created": datetime.now().isoformat(),
            "device_name": device.Name,
            "device_type": device.DeviceType,
            "serial": device.SerialNumber or "",
            "brightness": int(device.Brightness),
        }

        # Current FX
        current_fx = device.CurrentFX
        if current_fx and isinstance(current_fx, tuple) and len(current_fx) >= 1:
            profile["fx"] = current_fx[0]
            if len(current_fx) >= 2 and current_fx[1]:
                profile["fx_args"] = current_fx[1]

        # LED states
        led_states = {}
        for led in device.SupportedLeds or []:
            try:
                state = service.get_led_state(device, led)
                if state:
                    led_states[led] = state
            except Exception:
                pass

        if led_states:
            profile["leds"] = led_states

        # Active layers/renderers
        try:
            layers = service.get_active_layers(device)
            if layers:
                profile["layers"] = layers
        except Exception:
            pass

        return profile

    # ─────────────────────────────────────────────────────────────────────────
    # Load profile
    # ─────────────────────────────────────────────────────────────────────────

    def _load(self, args: Namespace) -> int:
        """Load a saved profile onto a device."""
        service = get_device_service()
        try:
            device = service.require_device(args.device_spec)
        except ValueError as e:
            self.print(self.out.error(str(e)))
            return 1

        name = args.name
        path = PROFILE_DIR / f"{name}.json"

        if not path.exists():
            self.print(self.out.error(f"Profile '{name}' not found"))
            return 1

        try:
            profile = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            self.print(self.out.error(f"Invalid profile: {e}"))
            return 1

        # Apply profile
        errors = self._apply_profile(service, device, profile)

        if errors:
            self.print(self.out.warning(f"Loaded profile with {len(errors)} warning(s)"))
            for err in errors:
                self.print(self.out.muted(f"  {err}"))
        else:
            self.print(self.out.success(f"Loaded profile: {name}"))

        return 0

    def _apply_profile(self, service, device, profile: dict[str, Any]) -> list[str]:
        """Apply profile settings to device. Returns list of errors."""
        errors: list[str] = []

        # Brightness
        if "brightness" in profile:
            try:
                device.Brightness = profile["brightness"]
            except Exception as e:
                errors.append(f"brightness: {e}")

        # FX
        if "fx" in profile:
            try:
                fx_name = profile["fx"]
                fx_args = profile.get("fx_args", {})
                service.set_fx(device, fx_name, fx_args)
            except Exception as e:
                errors.append(f"fx: {e}")

        # LEDs
        if "leds" in profile:
            for led, state in profile["leds"].items():
                try:
                    service.set_led(device, led, state)
                except Exception as e:
                    errors.append(f"led {led}: {e}")

        # Layers (if supported)
        if "layers" in profile:
            for layer_info in profile["layers"]:
                try:
                    renderer = layer_info.get("renderer")
                    if renderer:
                        zindex = layer_info.get("zindex", -1)
                        traits = layer_info.get("args", {})
                        service.add_renderer(device, renderer, zindex, traits)
                except Exception as e:
                    errors.append(f"layer {layer_info.get('renderer', '?')}: {e}")

        return errors

    # ─────────────────────────────────────────────────────────────────────────
    # Show profile
    # ─────────────────────────────────────────────────────────────────────────

    def _show(self, args: Namespace) -> int:
        """Show contents of a saved profile."""
        name = args.name
        path = PROFILE_DIR / f"{name}.json"

        if not path.exists():
            self.print(self.out.error(f"Profile '{name}' not found"))
            return 1

        try:
            profile = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            self.print(self.out.error(f"Invalid profile: {e}"))
            return 1

        self.print()
        self.print(self.out.header(f" Profile: {name}"))
        self.print()

        key_width = 15

        # Basic info
        for key in ["device_name", "device_type", "serial", "created"]:
            if key in profile:
                value = profile[key]
                if key == "created":
                    try:
                        dt = datetime.fromisoformat(value)
                        value = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass
                self.print(self.out.table_row(key_width, self.out.key(key), str(value)))

        self.print()

        # State info
        if "brightness" in profile:
            bar = self.out.progress_bar(profile["brightness"], 100, width=15)
            self.print(self.out.table_row(key_width, self.out.key("brightness"), bar))

        if "fx" in profile:
            fx_display = profile["fx"]
            if profile.get("fx_args"):
                args_str = ", ".join(f"{k}={v}" for k, v in profile["fx_args"].items())
                fx_display = f"{fx_display} ({args_str})"
            self.print(self.out.table_row(key_width, self.out.key("effect"), fx_display))

        if "leds" in profile:
            self.print(
                self.out.table_row(
                    key_width, self.out.key("leds"), ", ".join(profile["leds"].keys())
                )
            )

        if "layers" in profile:
            renderers = [l.get("renderer", "?") for l in profile["layers"]]
            self.print(self.out.table_row(key_width, self.out.key("layers"), ", ".join(renderers)))

        self.print()
        self.print(self.out.muted(f"  File: {self.out.path(str(path))}"))
        self.print()

        return 0

    # ─────────────────────────────────────────────────────────────────────────
    # Delete profile
    # ─────────────────────────────────────────────────────────────────────────

    def _delete(self, args: Namespace) -> int:
        """Delete a saved profile."""
        name = args.name
        path = PROFILE_DIR / f"{name}.json"

        if not path.exists():
            self.print(self.out.error(f"Profile '{name}' not found"))
            return 1

        path.unlink()
        self.print(self.out.success(f"Deleted profile: {name}"))
        return 0
