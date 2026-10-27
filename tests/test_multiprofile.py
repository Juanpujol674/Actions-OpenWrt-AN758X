#!/usr/bin/env python3
"""Stdlib tests for multi-profile merge, including a conflict like 2026-10-26 CI."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/make-multiprofile-config.py'
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location('multi', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BuildConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.configs = self.dir / 'configs'
        self.configs.mkdir()

    def add(self, profile, contents):
        (self.configs / (profile + '.config')).write_text(contents, encoding='utf8')

    def run_merge(self, soc):
        return subprocess.run([sys.executable, str(SCRIPT), soc, '--configs', str(self.configs),
                               '--output', str(self.dir / '.config')], capture_output=True, text=True)

    def test_device_specific_wifi_and_inline_comments(self):
        for name in module.PROFILES['an7581']:
            wifi = name in ('fiberhome_hg5585f-cu', 'fiberhome_hg5585f-ct', 'znxt_zn515xg-d')
            self.add(name, 'CONFIG_TARGET_ROOTFS_SQUASHFS=y\n'
                     'CONFIG_PACKAGE_busybox=y\n'
                     + ('CONFIG_PACKAGE_kmod-mt7915e=y    # wireless support\n' if wifi else
                        '# CONFIG_PACKAGE_kmod-mt7915e is not set\n'))
        result = self.run_merge('an7581')
        self.assertEqual(result.returncode, 0, result.stderr)
        cfg = module.parse(self.dir / '.config')
        self.assertEqual(cfg['CONFIG_TARGET_PER_DEVICE_ROOTFS'], 'y')
        self.assertEqual(cfg['CONFIG_PACKAGE_kmod-mt7915e'], 'm')
        self.assertEqual(cfg['CONFIG_PACKAGE_busybox'], 'y')
        self.assertIn('kmod-mt7915e', cfg['CONFIG_TARGET_DEVICE_PACKAGES_airoha_an7581_DEVICE_fiberhome_hg5585f-cu'])
        self.assertNotIn('kmod-mt7915e', cfg['CONFIG_TARGET_DEVICE_PACKAGES_airoha_an7581_DEVICE_nokia_xg-040g-md-ubi'])
        self.assertEqual(len([x for x in cfg if x.startswith('CONFIG_TARGET_DEVICE_airoha_an7581_DEVICE_')]), 14)

    def test_mixed_y_and_m_with_existing_packages(self):
        a, b = module.PROFILES['an7583']
        self.add(a, 'CONFIG_TARGET_ROOTFS_SQUASHFS=y\nCONFIG_PACKAGE_test=y\n'
                    'CONFIG_TARGET_DEVICE_PACKAGES_airoha_an7583_DEVICE_nokia_xg-040g-mf="native-package -obsolete"\n')
        self.add(b, 'CONFIG_TARGET_ROOTFS_SQUASHFS=y\nCONFIG_PACKAGE_test=m\n')
        result = self.run_merge('an7583')
        self.assertEqual(result.returncode, 0, result.stderr)
        cfg = module.parse(self.dir / '.config')
        self.assertEqual(cfg['CONFIG_PACKAGE_test'], 'm')
        self.assertIn('native-package', cfg['CONFIG_TARGET_DEVICE_PACKAGES_airoha_an7583_DEVICE_nokia_xg-040g-mf'])
        self.assertIn(' test\"', cfg['CONFIG_TARGET_DEVICE_PACKAGES_airoha_an7583_DEVICE_nokia_xg-040g-mf'])

    def test_global_conflict_fails(self):
        a, b = module.PROFILES['an7583']
        self.add(a, 'CONFIG_TARGET_ROOTFS_PARTSIZE=128\n')
        self.add(b, 'CONFIG_TARGET_ROOTFS_PARTSIZE=256\n')
        result = self.run_merge('an7583')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('CONFIG_TARGET_ROOTFS_PARTSIZE', result.stderr)

    def test_missing_config_fails(self):
        self.add('nokia_xg-040g-mf', 'CONFIG_PACKAGE_busybox=y\n')
        result = self.run_merge('an7583')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing config', result.stderr)


if __name__ == '__main__':
    unittest.main()
