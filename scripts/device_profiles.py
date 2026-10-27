#!/usr/bin/env python3
"""Single image list for multiprofile selection, verification and publishing.

Only profiles defined by pbs05/ponwrt are listed.  A USB-SFP profile uses
its own upstream DTS and inherits software choices from the ordinary board.
"""
import argparse

PROFILES = {
    'an7581': [
        'fiberhome_hg5382a',
        'fiberhome_hg5585f-ct', 'fiberhome_hg5585f-ct-usb-sfp',
        'fiberhome_hg5585f-cu', 'fiberhome_hg5585f-cu-usb-sfp',
        'gemtek_w1700k-ubi', 'gemtek_xg2010g', 'h3c_hm2004-du',
        'nokia_xg-040g-md-ubi', 'nokia_xg-040g-md-ubi-usb-sfp',
        'nokia_xg-040g-tf-ubi', 'unionman_ung00a',
        'znxt_zn504xg-d', 'znxt_zn515xg-d',
    ],
    'an7583': ['nokia_xg-040g-mf', 'nokia_xg-040g-mf-ubi'],
}

CONFIG_SOURCES = {
    'fiberhome_hg5585f-ct-usb-sfp': 'fiberhome_hg5585f-ct',
    'fiberhome_hg5585f-cu-usb-sfp': 'fiberhome_hg5585f-cu',
    'nokia_xg-040g-md-ubi-usb-sfp': 'nokia_xg-040g-md-ubi',
}

# W1700K has no local config stub. Inherit the common software bundle only;
# upstream Device/gemtek_w1700k-ubi supplies its MT7996/PHY/board packages.
COMMON_SOFTWARE_PROFILES = {'gemtek_w1700k-ubi'}

# This workflow explicitly sets ADD_FTTR=false and does not clone the private
# FTTR feed. Do not emit unavailable packages into per-device rootfs lists.
PRIVATE_FTTR_PACKAGES = {
    'kmod-h3c-fmcs', 'h3c-fmcs-firmware', 'h3c-fttr-tools',
    'luci-app-fttr', 'luci-i18n-fttr-zh-cn',
}

# The ordinary MF image is a sysupgrade tar wrapped in .bin, not UBI .itb.
EXTENSION = {('an7583', 'nokia_xg-040g-mf'): 'bin'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('soc', choices=PROFILES)
    args = parser.parse_args()
    print('\n'.join(PROFILES[args.soc]))
