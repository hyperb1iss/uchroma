# D-Bus Modernization Plan (2026)

## Decisions

- Session bus only (single-user workflow).
- No trait schema versioning.
- Preserve `io.uchroma.DeviceManager` for compatibility.

## Goals

- Align with `org.freedesktop.DBus.ObjectManager` and standard properties signaling.
- Stabilize variant encoding and type signatures (less runtime coercion).
- Improve error reporting without breaking existing clients.

## Non-goals

- Switching to system bus or multi-user policy changes.
- Replacing the `GetCurrentFrame` payload mechanism (current sizes are small).
- Breaking API changes for CLI/GTK.

## Plan

1. Add ObjectManager support at `/io/uchroma` with `GetManagedObjects`,
   `InterfacesAdded`, and `InterfacesRemoved`.
2. Remove custom `PropertiesChanged` signals and use standard
   `org.freedesktop.DBus.Properties` emissions; wire client listeners.
3. Normalize `dbus_prepare` coercion (ints, numpy arrays, bytes,
   array-of-variants) and reuse it in GTK D-Bus helpers.
4. Raise `DBusError` for invalid inputs (unknown LED, renderer, etc.);
   update clients to handle exceptions.
5. Fix known client issues (GTK `set_effect`, AvailableLEDs getter typo).
6. Add unit coverage for `dbus_prepare` to lock in new behavior.
7. Run lint, typecheck, and tests after each stage.

## Acceptance Criteria

- `GetManagedObjects` returns all device paths and interfaces with typed properties.
- GTK model updates on `PropertiesChanged` and reflects external changes.
- `dbus_prepare` produces stable signatures; tests cover core cases.
- CLI and GTK keep working with the legacy `DeviceManager` API.

