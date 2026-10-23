#!/usr/bin/env bash
set -euo pipefail
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p package/custom
fetch() {
  local url=$1 ref=$2 dest=$3
  git init -q "$dest"
  git -C "$dest" remote add origin "$url"
  git -C "$dest" fetch --depth 1 origin "$ref"
  git -C "$dest" checkout -q --detach FETCH_HEAD
}
install_pkg() {
  local src=$1 name=$2
  test -f "$src/Makefile"
  # Disable installed feed links before providing the same package locally.
  find package/feeds -mindepth 2 -maxdepth 2 -name "$name" -type l -delete
  rm -rf "package/custom/$name"
  cp -a "$src" "package/custom/$name"
}
fetch https://github.com/vernesong/OpenClash.git e553e82e01c697aefbe1555261a503f425e00ccd "$tmp/openclash"
install_pkg "$tmp/openclash/luci-app-openclash" luci-app-openclash
fetch https://github.com/nikkinikki-org/OpenWrt-nikki.git 78e1a751d55ed0762811f054ee699049473da7b8 "$tmp/nikki"
for p in nikki luci-app-nikki mihomo-meta; do install_pkg "$tmp/nikki/$p" "$p"; done
fetch https://github.com/nikkinikki-org/OpenWrt-momo.git f177d79d88ced747c74779e2fddc1e5b50663010 "$tmp/momo"
for p in momo luci-app-momo; do install_pkg "$tmp/momo/$p" "$p"; done
# sing-box comes from the packages feed; mihomo-meta provides Nikki's mihomo.
# The legacy custom plugin loader also installs pon-status: remove the feed
# link so buildroot sees exactly one package definition.
find package/feeds -mindepth 2 -maxdepth 2 -name luci-app-pon-status -type l -delete
