#!/usr/bin/env bash
set -euo pipefail
soc="${1:?Usage: verify-multiprofile.sh an7581|an7583}"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
profiles_text="$(python3 "$script_dir/device_profiles.py" "$soc")"
mapfile -t profiles <<< "$profiles_text"
grep -Fxq 'CONFIG_TARGET_MULTI_PROFILE=y' .config || { echo 'Multi-profile not enabled after make defconfig' >&2; exit 1; }
grep -Fxq 'CONFIG_TARGET_PER_DEVICE_ROOTFS=y' .config || { echo 'Per-device rootfs not enabled; hardware-specific packages may leak across devices' >&2; exit 1; }
grep -Fxq "CONFIG_TARGET_airoha_${soc}=y" .config || { echo 'Wrong subtarget' >&2; exit 1; }
for profile in "${profiles[@]}"; do
  key="CONFIG_TARGET_DEVICE_airoha_${soc}_DEVICE_${profile}=y"
  grep -Fxq "$key" .config || { echo "Profile not selected: $profile ($key)" >&2; exit 1; }
done
echo "All ${#profiles[@]} profiles enabled for ${soc}"
