#!/usr/bin/env bash
set -euo pipefail
missing=0
for p in kmod-usb-net kmod-usb-net-rndis kmod-usb-net-cdc-ether kmod-usb-net-cdc-ncm kmod-usb-net-huawei-cdc-ncm kmod-usb-wdm luci-app-openclash luci-app-nikki luci-app-momo luci-app-onu airoha-pond airoha-ponctl airoha-pon-debug; do
  if ! grep -qx "CONFIG_PACKAGE_${p}=y" .config; then
    echo "::error::Required package missing after defconfig: $p"
    missing=1
  fi
done
exit "$missing"
