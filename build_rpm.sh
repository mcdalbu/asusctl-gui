#!/usr/bin/env bash
# build_rpm.sh — Build asusctl-gui RPM from source
# Usage: ./build_rpm.sh
#
# Requires: rpmdevtools, rpmbuild
#   Install with: sudo dnf install rpmdevtools rpm-build
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_NAME="asusctl-gui"
PKG_VERSION="1.0.0"
TARBALL="${PKG_NAME}-${PKG_VERSION}.tar.gz"
SPEC_FILE="${SCRIPT_DIR}/packaging/${PKG_NAME}.spec"

cd "$SCRIPT_DIR"

# ── Ensure rpmdev tree exists ─────────────────────────────────────────────────
echo "▸ Setting up RPM build tree..."
rpmdev-setuptree

SOURCES_DIR="${HOME}/rpmbuild/SOURCES"
SPECS_DIR="${HOME}/rpmbuild/SPECS"
RPMS_DIR="${HOME}/rpmbuild/RPMS/noarch"

# ── Create source tarball ─────────────────────────────────────────────────────
echo "▸ Creating source tarball: ${TARBALL}"

# Create a temporary staging directory with the proper prefix
STAGE_DIR="/tmp/${PKG_NAME}-${PKG_VERSION}"
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"

# Copy project files
cp -r asusctl_gui                      "$STAGE_DIR/"
cp -r data                             "$STAGE_DIR/"
cp asusctl-gui-launcher.py             "$STAGE_DIR/"
cp README.md                           "$STAGE_DIR/" 2>/dev/null || touch "$STAGE_DIR/README.md"

# LICENSE file
if [[ -f LICENSE ]]; then
    cp LICENSE "$STAGE_DIR/"
else
    cat > "$STAGE_DIR/LICENSE" <<'EOF'
GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007
(See https://www.gnu.org/licenses/gpl-3.0.html for the full text)
EOF
fi

# Build the tarball
tar -czf "${SOURCES_DIR}/${TARBALL}" -C /tmp "${PKG_NAME}-${PKG_VERSION}/"
rm -rf "$STAGE_DIR"

echo "  ✓ Tarball → ${SOURCES_DIR}/${TARBALL}"

# ── Copy spec ─────────────────────────────────────────────────────────────────
echo "▸ Copying spec file..."
cp "$SPEC_FILE" "${SPECS_DIR}/${PKG_NAME}.spec"
echo "  ✓ Spec → ${SPECS_DIR}/${PKG_NAME}.spec"

# ── Build RPM ─────────────────────────────────────────────────────────────────
echo "▸ Building RPM..."
rpmbuild -ba "${SPECS_DIR}/${PKG_NAME}.spec"

# ── Report ────────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════"
echo " ✓ Build complete! Output:"
find "${HOME}/rpmbuild/RPMS" -name "${PKG_NAME}*.rpm" -print
find "${HOME}/rpmbuild/SRPMS" -name "${PKG_NAME}*.rpm" -print
echo ""
echo " Install with:"
echo "   sudo rpm -ivh \$(find ~/rpmbuild/RPMS -name '${PKG_NAME}*.rpm' | tail -1)"
echo " Or:"
echo "   sudo dnf install \$(find ~/rpmbuild/RPMS -name '${PKG_NAME}*.rpm' | tail -1)"
echo "════════════════════════════════════════════════════════"
