Name:           uchroma
Version:        1.9.90
Release:        1%{?dist}
Summary:        Userspace RGB control for Razer Chroma peripherals
License:        LGPL-3.0-only
URL:            https://github.com/hyperbliss/uchroma
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz#/%{name}-%{version}.tar.gz

BuildRequires:  python3-devel
BuildRequires:  python3-installer
BuildRequires:  rust
BuildRequires:  cargo
BuildRequires:  maturin
BuildRequires:  systemd-rpm-macros

Requires:       python3-argcomplete
Requires:       python3-coloraide
Requires:       python3-colorlog
Requires:       python3-dbus-fast
Requires:       python3-evdev
Requires:       python3-frozendict
Requires:       python3-numpy
Requires:       python3-pyudev
Requires:       python3-ruamel-yaml
Requires:       python3-traitlets
Requires:       python3-wrapt

Recommends:     python3-gobject
Recommends:     libadwaita

%description
An advanced driver for the Razer Chroma line of peripherals.
Supports lighting effects, custom animations, and more.

%prep
%autosetup -n %{name}-%{version}

%build
make build MATURIN=maturin

%install
python3 -m installer --destdir=%{buildroot} target/wheels/*.whl
make install DESTDIR=%{buildroot}

%post
%systemd_user_post uchromad.service
udevadm control --reload-rules || :

%preun
%systemd_user_preun uchromad.service

%files
%license LICENSE
%doc README.md
%{_bindir}/uchroma
%{_bindir}/uchromad
%{_bindir}/uchroma-gtk
%{python3_sitearch}/uchroma/
%{python3_sitearch}/uchroma-*.dist-info/
%{_prefix}/lib/udev/rules.d/70-uchroma.rules
%{_prefix}/lib/systemd/user/uchromad.service
%{_datadir}/dbus-1/services/io.uchroma.service
%{_datadir}/applications/io.uchroma.gtk.desktop
%{_datadir}/icons/hicolor/scalable/apps/io.uchroma.svg

%changelog
* Sat Jan 18 2026 Stefanie Jane <stef@hyperbliss.tech> - 1.9.90-1
- Initial Fedora package with Rust native extensions
