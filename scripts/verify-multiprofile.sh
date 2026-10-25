#!/usr/bin/env bash
set -euo pipefail
soc="${1:?Usage: verify-multiprofile.sh an7581|an7583}"
case "$soc" in
  an7581) profiles=(fiberhome_hg5382a fiberhome_hg5585f-ct fiberhome_hg5585f-cu gemtek_xg2010g nokia_xg-040g-md-ubi nokia_xg-040g-tf-ubi unionman_ung00a znxt_zn504xg-d znxt_zn515xg-d) ;;
  an7583) profiles=(nokia_xg-040g-mf nokia_xg-040g-mf-ubi) ;;
  *) echo "Unsupported subtarget: $soc" >&2; exit 2 ;;
esac
grep -Fxq 'CONFIG_TARGET_MULTI_PROFILE=y' .config || { echo 'Multi-profile not enabled after make defconfig' >&2; exit 1; }
grep -Fxq "CONFIG_TARGET_airoha_${soc}=y" .config || { echo 'Wrong subtarget' >&2; exit 1; }
for profile in "${profiles[@]}"; do
  key="CONFIG_TARGET_DEVICE_airoha_${soc}_DEVICE_${profile}=y"
  grep -Fxq "$key" .config || { echo "Profile not selected: $profile ($key)" >&2; exit 1; }
done
echo "All ${#profiles[@]} profiles enabled for ${soc}"
