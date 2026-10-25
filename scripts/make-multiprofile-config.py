#!/usr/bin/env python3
"""Make a conservative OpenWrt multi-profile .config from existing device configs.

This refuses conflicting global settings rather than silently modifying the
contents of another device's rootfs. Run from the CI repository root.
"""
import argparse
from collections import defaultdict
from pathlib import Path
import re
import sys

PROFILES = {
    'an7581': [
        'fiberhome_hg5382a', 'fiberhome_hg5585f-ct', 'fiberhome_hg5585f-cu',
        'gemtek_xg2010g', 'nokia_xg-040g-md-ubi', 'nokia_xg-040g-tf-ubi',
        'unionman_ung00a', 'znxt_zn504xg-d', 'znxt_zn515xg-d',
    ],
    'an7583': ['nokia_xg-040g-mf', 'nokia_xg-040g-mf-ubi'],
}

SETTING = re.compile(r'^(CONFIG_[A-Za-z0-9_\-]+)=(.*)$')
UNSET = re.compile(r'^# (CONFIG_[A-Za-z0-9_\-]+) is not set$')


def parse(path):
    result = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        match = SETTING.fullmatch(line)
        if match:
            key, value = match.groups()
        else:
            match = UNSET.fullmatch(line)
            if not match:
                continue
            key, value = match.group(1), 'n'
        result[key] = value
    return result


def is_selector(key):
    if not key.startswith('CONFIG_TARGET_'):
        return False
    if key.startswith(('CONFIG_TARGET_ROOTFS_', 'CONFIG_TARGET_INITRAMFS_',
                       'CONFIG_TARGET_PER_DEVICE_ROOTFS', 'CONFIG_TARGET_SQUASHFS_',
                       'CONFIG_TARGET_EXT4FS_', 'CONFIG_TARGET_UBIFS_')):
        return False
    # Includes TARGET_<board> and TARGET_DEVICE_<board>_DEVICE_<name>
    return True


def emit(key, value):
    return f'# {key} is not set' if value == 'n' else f'{key}={value}'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('soc', choices=PROFILES)
    parser.add_argument('--configs', type=Path, default=Path('configs'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    data = {}
    for profile in PROFILES[args.soc]:
        path = args.configs / (profile + '.config')
        if not path.is_file():
            sys.exit(f'ERROR: missing config: {path}')
        data[profile] = parse(path)

    # Preserve per-device package declarations separately (if they exist).
    device_packages = {}
    global_settings = defaultdict(dict)
    for profile, cfg in data.items():
        for key, value in cfg.items():
            if key.startswith('CONFIG_TARGET_DEVICE_PACKAGES_'):
                suffix = f'airoha_{args.soc}_DEVICE_{profile}'
                if key == 'CONFIG_TARGET_DEVICE_PACKAGES_' + suffix:
                    device_packages[key] = value
                continue
            if not is_selector(key):
                global_settings[key][profile] = value

    conflicts = []
    for key, values in sorted(global_settings.items()):
        distinct = set(values.values())
        # Missing symbols in a minimal diffconfig are unknown, not 'n'.
        if len(distinct) > 1:
            summary = ', '.join(f'{p}={v}' for p, v in sorted(values.items()))
            conflicts.append(f'{key}: {summary}')
    if conflicts:
        print('ERROR: configurations disagree on global settings.', file=sys.stderr)
        print('A single build has a shared global package selection. Resolve',
              'these first, rather than risk changing a device firmware.', file=sys.stderr)
        print('\n'.join(conflicts[:80]), file=sys.stderr)
        if len(conflicts) > 80:
            print(f'... and {len(conflicts)-80} more conflicts', file=sys.stderr)
        sys.exit(2)

    settings = {k: next(iter(v.values())) for k, v in global_settings.items()}
    settings.update({
        'CONFIG_TARGET_airoha': 'y',
        'CONFIG_TARGET_airoha_' + args.soc: 'y',
        'CONFIG_TARGET_MULTI_PROFILE': 'y',
        'CONFIG_TARGET_PER_DEVICE_ROOTFS': 'y',
        'CONFIG_TARGET_ROOTFS_INITRAMFS': 'n',
    })
    for profile in PROFILES[args.soc]:
        settings[f'CONFIG_TARGET_DEVICE_airoha_{args.soc}_DEVICE_{profile}'] = 'y'
    settings.update(device_packages)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    content = ('# Generated from configs/<device>.config; do not edit by hand.\n'
               + '\n'.join(emit(key, val) for key, val in sorted(settings.items()))
               + '\n')
    args.output.write_text(content, encoding='utf-8')
    print(f'Generated {args.output} from {len(data)} {args.soc} profiles')
    print('\n'.join('  ' + p for p in PROFILES[args.soc]))


if __name__ == '__main__':
    main()
