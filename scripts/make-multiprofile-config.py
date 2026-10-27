#!/usr/bin/env python3
"""Merge OpenWrt device configs into a safe per-device-rootfs multi-profile config.

Packages that are universal remain CONFIG_PACKAGE_foo=y. Packages required by
only a subset are built as modules (=m) and included only in those devices via
CONFIG_TARGET_DEVICE_PACKAGES_... .  Non-package setting conflicts are errors.
"""
import argparse
from collections import defaultdict
from pathlib import Path
import re
import sys
from device_profiles import (PROFILES, CONFIG_SOURCES,
                             COMMON_SOFTWARE_PROFILES, PRIVATE_FTTR_PACKAGES)

SETTING = re.compile(r'^(CONFIG_[A-Za-z0-9_\-]+)=(.*)$')
UNSET = re.compile(r'^# (CONFIG_[A-Za-z0-9_\-]+) is not set(?:\s*#.*)?$')


def parse(path):
    result = {}
    for no, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        line = raw.strip()
        found = SETTING.fullmatch(line)
        if found:
            key, value = found.groups()
            # Some configs contain human-readable inline comments following '=y'.
            # These comments must NOT become part of the Kconfig value.
            if not value.startswith('"'):
                value = value.split(' #', 1)[0].strip()
            elif value.endswith('"') is False:
                # Keep quoted options with trailing comments intact up to last '"'.
                ending = value.rfind('"')
                if ending > 0:
                    value = value[:ending + 1]
            if not value:
                sys.exit(f'ERROR: empty Kconfig value: {path}:{no} {key}')
        else:
            found = UNSET.fullmatch(line)
            if not found:
                continue
            key, value = found.group(1), 'n'
        result[key] = value
    return result


def selected_target(key):
    """Only target selection keys, not target image or filesystem options."""
    return (key in {'CONFIG_TARGET_airoha', 'CONFIG_TARGET_airoha_an7581',
                    'CONFIG_TARGET_airoha_an7583', 'CONFIG_TARGET_MULTI_PROFILE',
                    'CONFIG_TARGET_PER_DEVICE_ROOTFS', 'CONFIG_TARGET_ALL_PROFILES'}
            or key.startswith('CONFIG_TARGET_DEVICE_')
            or key.startswith('CONFIG_TARGET_PROFILE'))


def emit(key, value):
    return f'# {key} is not set' if value == 'n' else f'{key}={value}'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('soc', choices=PROFILES)
    p.add_argument('--configs', type=Path, default=Path('configs'))
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--source-image-dir', type=Path,
                   help='Check selected profiles exist in the cloned source')
    args = p.parse_args()

    names = PROFILES[args.soc]
    if args.source_image_dir:
        image_makefile = args.source_image_dir / (args.soc + '.mk')
        available = set(re.findall(r'^TARGET_DEVICES\s*\+=\s*(\S+)\s*$',
                                   image_makefile.read_text(encoding='utf-8'), re.M))
        missing = set(names) - available
        if missing:
            sys.exit('ERROR: source lacks selected device(s): ' + ', '.join(sorted(missing)))
    sources = {}
    for profile in names:
        if profile in COMMON_SOFTWARE_PROFILES:
            continue
        config_profile = CONFIG_SOURCES.get(profile, profile)
        path = args.configs / (config_profile + '.config')
        if not path.is_file():
            sys.exit(f'ERROR: missing config: {path}')
        sources[profile] = parse(path)
        if config_profile != profile:
            old_key = f'CONFIG_TARGET_DEVICE_PACKAGES_airoha_{args.soc}_DEVICE_{config_profile}'
            new_key = f'CONFIG_TARGET_DEVICE_PACKAGES_airoha_{args.soc}_DEVICE_{profile}'
            sources[profile][new_key] = sources[profile].get(old_key, '""')

    for cfg in sources.values():
        for key in list(cfg):
            if key.startswith('CONFIG_FTTR_'):
                del cfg[key]
        for package in PRIVATE_FTTR_PACKAGES:
            cfg.pop('CONFIG_PACKAGE_' + package, None)
        for key, value in list(cfg.items()):
            if key.startswith('CONFIG_TARGET_DEVICE_PACKAGES_'):
                tokens = value.strip('"').split()
                cfg[key] = '"' + ' '.join(t for t in tokens
                                         if t.lstrip('-') not in PRIVATE_FTTR_PACKAGES) + '"'

    # Add boards without local config stubs using the intersection of existing
    # package selections. Hardware packages remain upstream device defaults.
    common_packages = {
        key: 'y' for key in next(iter(sources.values()))
        if key.startswith('CONFIG_PACKAGE_')
        and all(cfg.get(key) == 'y' for cfg in sources.values())
    }
    for profile in names:
        if profile in COMMON_SOFTWARE_PROFILES:
            sources[profile] = dict(common_packages)

    extra_keys = {name: f'CONFIG_TARGET_DEVICE_PACKAGES_airoha_{args.soc}_DEVICE_{name}'
                  for name in names}
    # All non-package settings must agree whenever they are explicitly set.
    shared = defaultdict(dict)
    packages = set()
    for name, cfg in sources.items():
        for key, val in cfg.items():
            if key.startswith('CONFIG_TARGET_DEVICE_PACKAGES_') or selected_target(key):
                continue
            if key.startswith('CONFIG_PACKAGE_'):
                packages.add(key)
            else:
                shared[key][name] = val
    conflicts = []
    for key, values in sorted(shared.items()):
        if len(set(values.values())) > 1:
            conflicts.append(f'{key}: ' + ', '.join(f'{n}={v}' for n, v in sorted(values.items())))
    if conflicts:
        print('ERROR: non-package build settings differ; cannot safely merge.', file=sys.stderr)
        print('\n'.join(conflicts[:80]), file=sys.stderr)
        if len(conflicts) > 80:
            print(f'... plus {len(conflicts)-80} more', file=sys.stderr)
        sys.exit(2)

    merged = {key: next(iter(values.values())) for key, values in shared.items()}
    merged.update({
        'CONFIG_TARGET_airoha': 'y',
        f'CONFIG_TARGET_airoha_{args.soc}': 'y',
        'CONFIG_TARGET_MULTI_PROFILE': 'y',
        'CONFIG_TARGET_PER_DEVICE_ROOTFS': 'y',
        'CONFIG_TARGET_ALL_PROFILES': 'n',
        'CONFIG_TARGET_ROOTFS_INITRAMFS': 'n',
    })
    for name in names:
        merged[f'CONFIG_TARGET_DEVICE_airoha_{args.soc}_DEVICE_{name}'] = 'y'

    additions = {name: [] for name in names}
    per_device_count = 0
    for key in sorted(packages):
        # Missing =n is an intentional choice for device-specific config stubs.
        options = {name: sources[name].get(key, 'n') for name in names}
        invalid = {v for v in options.values() if v not in {'y', 'm', 'n'}}
        if invalid:
            sys.exit(f'ERROR: package {key} has unexpected value(s): {invalid}')
        if all(v == 'y' for v in options.values()):
            merged[key] = 'y'
        elif any(v == 'y' for v in options.values()):
            # A built-as-module package can be installed in individual images.
            merged[key] = 'm'
            per_device_count += 1
            package_name = key[len('CONFIG_PACKAGE_'):]
            for name, value in options.items():
                if value == 'y':
                    additions[name].append(package_name)
        elif any(v == 'm' for v in options.values()):
            merged[key] = 'm'
        # All-n symbols are omitted so OpenWrt can apply normal defaults.

    for name in names:
        original = sources[name].get(extra_keys[name], '""')
        if not (original.startswith('"') and original.endswith('"')):
            sys.exit(f'ERROR: malformed {extra_keys[name]}: {original!r}')
        tokens = original[1:-1].split()
        for pkg in additions[name]:
            tokens = [tok for tok in tokens if tok != f'-{pkg}']
            if pkg not in tokens:
                tokens.append(pkg)
        merged[extra_keys[name]] = '"' + ' '.join(tokens) + '"'

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        '# Generated from configs/<device>.config; do not edit by hand.\n'
        + '\n'.join(emit(key, val) for key, val in sorted(merged.items())) + '\n',
        encoding='utf-8'
    )
    print(f'Generated {args.output}: {args.soc}, {len(names)} devices;'
          f' {per_device_count} packages allocated per device')
    for name in names:
        print(f'  {name}: {len(additions[name])} additional device packages')


if __name__ == '__main__':
    main()
