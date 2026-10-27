#!/usr/bin/env python3
"""Copy ONLY usable sysupgrade images for selected targets into a release dir."""
import argparse
from pathlib import Path
import shutil
import sys
from device_profiles import PROFILES, EXTENSION


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('soc', choices=PROFILES)
    ap.add_argument('--images', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if not args.images.is_dir():
        sys.exit(f'ERROR: image directory does not exist: {args.images}')
    args.output.mkdir(parents=True, exist_ok=True)
    copied, errors = [], []
    for profile in PROFILES[args.soc]:
        ext = EXTENSION.get((args.soc, profile), 'itb')
        candidates = sorted(args.images.glob(f'*-{profile}-squashfs-sysupgrade.{ext}'))
        if len(candidates) != 1:
            errors.append(f'{profile}: expected exactly 1 *-squashfs-sysupgrade.{ext}, found {len(candidates)}')
            continue
        source = candidates[0]
        if source.stat().st_size == 0:
            errors.append(f'{profile}: 0 byte image: {source}')
            continue
        shutil.copy2(source, args.output / source.name)
        copied.append(source.name)
    print('Selected sysupgrade images:')
    for name in copied:
        print('  ' + name)
    if errors:
        print('ERROR: incomplete multi-profile image set:', file=sys.stderr)
        for err in errors:
            print('  ' + err, file=sys.stderr)
        # Remove partial stage so neither Artifact nor Release can be published.
        for path in args.output.iterdir():
            if path.is_file():
                path.unlink()
        sys.exit(2)
    print(f'OK: {len(copied)} sysupgrade-only images in {args.output}')


if __name__ == '__main__':
    main()
