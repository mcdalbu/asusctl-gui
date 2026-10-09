#!/usr/bin/env bash
# Build in an isolated temporary tree; keep packages in this checkout.
set -euo pipefail
# RPM helper scripts must use Fedora tools, even when Homebrew precedes them.
export PATH="/usr/bin:/bin:$PATH"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_NAME="asusctl-gui"
PKG_VERSION="1.1.0"
OUTPUT_ROOT="${SCRIPT_DIR}/build/rpmbuild"
WORK_DIR="$(mktemp -d /tmp/asusctl-gui-build.XXXXXX)"
trap 'rm -rf "$WORK_DIR"' EXIT
BUILD_ROOT="${WORK_DIR}/rpmbuild"
mkdir -p "${BUILD_ROOT}"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS,tmp}
SOURCE_DIR="${WORK_DIR}/${PKG_NAME}-${PKG_VERSION}"
mkdir -p "$SOURCE_DIR"
cp -r "${SCRIPT_DIR}/asusctl_gui" "${SCRIPT_DIR}/data" "${SCRIPT_DIR}/tests" "${SCRIPT_DIR}/docs" "$SOURCE_DIR/"
cp "${SCRIPT_DIR}/asusctl-gui-launcher.py" "${SCRIPT_DIR}/README.md" "${SCRIPT_DIR}/LICENSE" "$SOURCE_DIR/"
find "$SOURCE_DIR" -type d -name __pycache__ -exec rm -rf {} +
tar -czf "${BUILD_ROOT}/SOURCES/${PKG_NAME}-${PKG_VERSION}.tar.gz" -C "$WORK_DIR" "${PKG_NAME}-${PKG_VERSION}"
cp "${SCRIPT_DIR}/packaging/${PKG_NAME}.spec" "${BUILD_ROOT}/SPECS/"
rpmbuild --define "_topdir ${BUILD_ROOT}" --define "_tmppath ${BUILD_ROOT}/tmp" -ba "${BUILD_ROOT}/SPECS/${PKG_NAME}.spec"
mkdir -p "${OUTPUT_ROOT}/RPMS" "${OUTPUT_ROOT}/SRPMS"
cp -r "${BUILD_ROOT}/RPMS/." "${OUTPUT_ROOT}/RPMS/"
cp -r "${BUILD_ROOT}/SRPMS/." "${OUTPUT_ROOT}/SRPMS/"
find "${OUTPUT_ROOT}/RPMS" "${OUTPUT_ROOT}/SRPMS" -name '*.rpm' -print
