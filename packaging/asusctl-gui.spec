Name:           asusctl-gui
Version:        1.1.2
Release:        1%{?dist}
Summary:        GTK4/Libadwaita controls for ASUS Vivobook laptops
License:        GPL-3.0-or-later
URL:            https://github.com/mcdalbu/asusctl-gui
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  python3-devel >= 3.15
Requires:       python3 >= 3.15
Requires:       python3-gobject >= 3.42
Requires:       gtk4 >= 4.10
Requires:       libadwaita >= 1.4
Requires:       asusctl >= 6.3.8
Requires:       upower

%description
Native GTK4/Libadwaita interface in Brazilian Portuguese for ASUS laptops,
including Vivobook S5406. Controls available asusd power profiles, automatic
profiles on AC/battery, battery charge limits, and keyboard brightness via
UPower. Hardware capabilities are discovered without changing settings.

%prep
%autosetup

%build
# Pure Python.

%install
install -d %{buildroot}%{python3_sitelib}/asusctl_gui
cp -pr asusctl_gui/. %{buildroot}%{python3_sitelib}/asusctl_gui/
find %{buildroot}%{python3_sitelib}/asusctl_gui -type d -name __pycache__ -exec rm -rf {} +
install -Dpm755 asusctl-gui-launcher.py %{buildroot}%{_bindir}/asusctl-gui
install -Dpm644 data/asusctl-gui.desktop %{buildroot}%{_datadir}/applications/asusctl-gui.desktop
install -Dpm644 data/asusctl-gui.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/asusctl-gui.svg
install -Dpm644 data/org.asuslinux.AsusctlGui.metainfo.xml %{buildroot}%{_datadir}/metainfo/org.asuslinux.AsusctlGui.metainfo.xml

%check
%{__python3} -m unittest discover -s tests -v

%files
%license LICENSE
%doc README.md docs/VALIDACAO.md
%{python3_sitelib}/asusctl_gui/
%{_bindir}/asusctl-gui
%{_datadir}/applications/asusctl-gui.desktop
%{_datadir}/icons/hicolor/scalable/apps/asusctl-gui.svg
%{_datadir}/metainfo/org.asuslinux.AsusctlGui.metainfo.xml

%changelog
* Tue Nov 03 2026 ASUS Control contributors - 1.1.2-1
- Target Fedora 45 with Python 3.15
- Rebuild using distribution Python paths and ABI dependencies

* Sat Oct 31 2026 ASUS Control contributors - 1.1.1-1
- Require the asusctl CLI version used by this interface
- Document automatic dependency installation with DNF
- Publish binary/source RPMs with SHA-256 checksums

* Fri Oct 09 2026 ASUS Control contributors - 1.1.0-2
- Replace the application icon with the ASUS wordmark and adjustment controls

* Fri Oct 09 2026 ASUS Control contributors - 1.1.0-1
- Vivobook capability discovery, UPower keyboard brightness and native adaptive UI
- Report backend failures and remove unsupported ScreenPad/Aura controls
- Use distribution Python macros and valid AppStream metadata
