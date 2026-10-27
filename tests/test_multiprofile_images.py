"""Regression tests for image selection; no toolchain or firmware build needed."""
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from device_profiles import PROFILES, EXTENSION, PRIVATE_FTTR_PACKAGES


def module(filename):
    spec = importlib.util.spec_from_file_location(filename.replace('-', '_'), SCRIPTS / filename)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


config_module = module('make-multiprofile-config.py')
release_module = module('make-multiprofile-release.py')


class MultiprofileImages(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def run_script(self, script, *args, ok=True):
        result = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                                text=True, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def generate(self, soc):
        dest = self.work / (soc + '.config')
        self.run_script('make-multiprofile-config.py', soc, '--configs', ROOT / 'configs',
                        '--output', dest)
        return config_module.parse(dest)

    def create_images(self, soc):
        images = self.work / 'images'
        images.mkdir()
        for profile in PROFILES[soc]:
            ext = EXTENSION.get((soc, profile), 'itb')
            (images / f'ponwrt-airoha-{soc}-{profile}-squashfs-sysupgrade.{ext}').write_bytes(b'fixture')
        (images / 'w1700k-chainload-uboot.itb').write_bytes(b'bootloader')
        (images / 'w1700k-recovery.itb').write_bytes(b'recovery')
        return images

    def test_all_profiles_are_selected_and_variant_packages_match(self):
        cfg = self.generate('an7581')
        selected = {k for k, v in cfg.items()
                    if k.startswith('CONFIG_TARGET_DEVICE_airoha_') and v == 'y'}
        self.assertEqual(len(selected), 14)
        for profile in PROFILES['an7581']:
            self.assertEqual(cfg[f'CONFIG_TARGET_DEVICE_airoha_an7581_DEVICE_{profile}'], 'y')
        for ordinary in ('fiberhome_hg5585f-ct', 'fiberhome_hg5585f-cu', 'nokia_xg-040g-md-ubi'):
            key = 'CONFIG_TARGET_DEVICE_PACKAGES_airoha_an7581_DEVICE_'
            self.assertEqual(cfg[key + ordinary], cfg[key + ordinary + '-usb-sfp'])
        for required in ('luci-app-openclash', 'luci-app-nikki', 'luci-app-momo',
                         'kmod-usb-net-huawei-cdc-ncm', 'kmod-usb-wdm'):
            self.assertEqual(cfg['CONFIG_PACKAGE_' + required], 'y')
        self.assertEqual(cfg['CONFIG_TARGET_PER_DEVICE_ROOTFS'], 'y')
        extras = '\n'.join(v for k, v in cfg.items() if k.startswith('CONFIG_TARGET_DEVICE_PACKAGES_'))
        for private in PRIVATE_FTTR_PACKAGES:
            self.assertNotIn(private, extras)
            self.assertNotIn('CONFIG_PACKAGE_' + private, cfg)

    def test_an7583_device_selection_is_unchanged(self):
        cfg = self.generate('an7583')
        selected = {k for k, v in cfg.items()
                    if k.startswith('CONFIG_TARGET_DEVICE_airoha_') and v == 'y'}
        self.assertEqual(len(selected), 2)

    def test_source_without_usb_sfp_profile_fails_before_build(self):
        source = self.work / 'source'
        source.mkdir()
        (source / 'an7581.mk').write_text('\n'.join(
            f'TARGET_DEVICES += {name}' for name in PROFILES['an7581'] if 'usb-sfp' not in name))
        result = self.run_script('make-multiprofile-config.py', 'an7581',
                                 '--configs', ROOT / 'configs', '--output', self.work / '.config',
                                 '--source-image-dir', source, ok=False)
        self.assertIn('source lacks selected device', result.stderr)
        self.assertIn('fiberhome_hg5585f-ct-usb-sfp', result.stderr)

    def test_stages_all_fourteen_sysupgrades_without_bootloaders(self):
        images = self.create_images('an7581')
        stage = self.work / 'release'
        self.run_script('stage-only-upgrades.py', 'an7581', '--images', images, '--output', stage)
        self.assertEqual(len(list(stage.iterdir())), 14)
        self.assertEqual(len(list(stage.glob('*usb-sfp*'))), 3)
        self.assertFalse(any('recovery' in p.name or 'uboot' in p.name for p in stage.iterdir()))
        release_module.prepare(images, stage, 'an7581', self.work / 'metadata',
                               datetime(2026, 10, 27, 12, tzinfo=timezone.utc))
        self.assertEqual(len(list(stage.glob('*-2026.10.27-12.00.00-squashfs-sysupgrade.itb'))), 14)
        notes = (self.work / 'metadata/release-notes.md').read_text(encoding='utf-8')
        self.assertIn('USB-SFP', notes)
        self.assertIn('HM2004-DU', notes)
        for image in stage.iterdir():
            self.assertIn(image.name, notes)

    def test_missing_variant_prevents_partial_release(self):
        images = self.create_images('an7581')
        next(images.glob('*fiberhome_hg5585f-ct-usb-sfp-*')).unlink()
        stage = self.work / 'release'
        result = self.run_script('stage-only-upgrades.py', 'an7581', '--images', images,
                                 '--output', stage, ok=False)
        self.assertIn('fiberhome_hg5585f-ct-usb-sfp', result.stderr)
        self.assertEqual(list(stage.iterdir()), [])

    def test_mf_binary_and_ubi_images_remain_distinct(self):
        images = self.create_images('an7583')
        stage = self.work / 'release'
        self.run_script('stage-only-upgrades.py', 'an7583', '--images', images, '--output', stage)
        self.assertEqual(len(list(stage.glob('*.bin'))), 1)
        self.assertEqual(len(list(stage.glob('*.itb'))), 1)


if __name__ == '__main__':
    unittest.main()
