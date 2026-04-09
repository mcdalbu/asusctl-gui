Name:           asusctl-gui
Version:        1.0.0
Release:        1%{?dist}
Summary:        GTK4 graphical interface for the asusd/asusctl ASUS laptop daemon

License:        GPLv3+
URL:            https://asus-linux.org
Source0:        %{name}-%{version}.tar.gz

# ── Build deps ─────────────────────────────────────────────────────────────────
BuildArch:      noarch
BuildRequires:  python3-setuptools

%global python3_sitelib /usr/lib/python3.14/site-packages

# ── Runtime deps ───────────────────────────────────────────────────────────────
Requires:       python3 >= 3.11
Requires:       python3-gobject >= 3.42
Requires:       gtk4 >= 4.10
Requires:       libadwaita >= 1.4
# The whole point — asusctl must be present
Requires:       asusctl

%description
asusctl-gui provides a modern GTK4/Adwaita graphical front-end for the
asusd daemon on ASUS ROG and TUF laptops running Linux.

It allows the user to:
  • Switch between power profiles (Quiet / Balanced / Performance)
  • Set and monitor battery charge limits (20–100 %)
  • Configure charging mode via firmware attributes
  • Adjust screenpad brightness and gamma
  • View supported hardware features and asusd version info

Feature detection is automatic: sections for unsupported hardware are hidden.

# ── Prep ───────────────────────────────────────────────────────────────────────
%prep
%autosetup

# ── Build ──────────────────────────────────────────────────────────────────────
%build
# Pure Python — nothing to compile.

# ── Install ────────────────────────────────────────────────────────────────────
%install
# Python package
install -d %{buildroot}%{python3_sitelib}/asusctl_gui/backend
install -d %{buildroot}%{python3_sitelib}/asusctl_gui/pages

install -p -m 644 asusctl_gui/__init__.py        %{buildroot}%{python3_sitelib}/asusctl_gui/
install -p -m 644 asusctl_gui/main.py            %{buildroot}%{python3_sitelib}/asusctl_gui/
install -p -m 644 asusctl_gui/window.py          %{buildroot}%{python3_sitelib}/asusctl_gui/
install -p -m 644 asusctl_gui/style.css          %{buildroot}%{python3_sitelib}/asusctl_gui/
install -p -m 644 asusctl_gui/backend/__init__.py  %{buildroot}%{python3_sitelib}/asusctl_gui/backend/
install -p -m 644 asusctl_gui/backend/asusctl.py   %{buildroot}%{python3_sitelib}/asusctl_gui/backend/
install -p -m 644 asusctl_gui/backend/system_info.py %{buildroot}%{python3_sitelib}/asusctl_gui/backend/
install -p -m 644 asusctl_gui/pages/__init__.py      %{buildroot}%{python3_sitelib}/asusctl_gui/pages/
install -p -m 644 asusctl_gui/pages/profile_page.py  %{buildroot}%{python3_sitelib}/asusctl_gui/pages/
install -p -m 644 asusctl_gui/pages/battery_page.py  %{buildroot}%{python3_sitelib}/asusctl_gui/pages/
install -p -m 644 asusctl_gui/pages/backlight_page.py %{buildroot}%{python3_sitelib}/asusctl_gui/pages/
install -p -m 644 asusctl_gui/pages/info_page.py     %{buildroot}%{python3_sitelib}/asusctl_gui/pages/

# Launcher binary
install -d %{buildroot}%{_bindir}
install -p -m 755 asusctl-gui-launcher.py %{buildroot}%{_bindir}/asusctl-gui

# Desktop entry
install -d %{buildroot}%{_datadir}/applications
install -p -m 644 data/asusctl-gui.desktop \
    %{buildroot}%{_datadir}/applications/asusctl-gui.desktop

# Icon — scalable SVG
install -d %{buildroot}%{_datadir}/icons/hicolor/scalable/apps
install -p -m 644 data/asusctl-gui.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/asusctl-gui.svg

# AppStream metainfo
install -d %{buildroot}%{_datadir}/metainfo
install -p -m 644 data/org.asuslinux.AsusctlGui.metainfo.xml \
    %{buildroot}%{_datadir}/metainfo/

# ── Post-install ───────────────────────────────────────────────────────────────
%post
/bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :

%postun
if [ $1 -eq 0 ] ; then
    /bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null
    /usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :
fi

%posttrans
/usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :

# ── Files ──────────────────────────────────────────────────────────────────────
%files
%license LICENSE
%doc README.md
%{python3_sitelib}/asusctl_gui/
%{_bindir}/asusctl-gui
%{_datadir}/applications/asusctl-gui.desktop
%{_datadir}/icons/hicolor/scalable/apps/asusctl-gui.svg
%{_datadir}/metainfo/org.asuslinux.AsusctlGui.metainfo.xml

# ── Changelog ──────────────────────────────────────────────────────────────────
%changelog
* Thu Apr 09 2026 asusctl-gui Maintainer <noreply@asus-linux.org> - 1.0.0-1
- Initial release for Fedora 43
- Power profile switching (Quiet / Balanced / Performance)
- Battery charge limit slider with live badge
- Charge mode via armoury firmware attributes
- Backlight / screenpad brightness control
- Feature auto-detection based on supported asusd interfaces
