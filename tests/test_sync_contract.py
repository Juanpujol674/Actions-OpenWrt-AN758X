"""Keep fork-specific build contracts intact during upstream synchronization."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('sync_config',ROOT/'scripts/make-multiprofile-config.py')
parser=importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)

class SyncContractTests(unittest.TestCase):
    def test_every_local_config_preserves_public_bundle_without_old_onu_ui(self):
        for path in (ROOT/'configs').glob('*.config'):
            with self.subTest(profile=path.name):
                cfg=parser.parse(path)
                for pkg in ('luci-app-openclash','luci-app-nikki','luci-app-momo',
                            'luci-app-onu','airoha-pond','airoha-ponctl',
                            'kmod-usb-net','kmod-usb-net-rndis','kmod-usb-net-cdc-ether',
                            'kmod-usb-net-cdc-ncm','kmod-usb-net-huawei-cdc-ncm','kmod-usb-wdm'):
                    self.assertEqual(cfg.get('CONFIG_PACKAGE_'+pkg),'y',pkg)
                for pkg in ('luci-app-pon','luci-app-iptv'):
                    self.assertEqual(cfg.get('CONFIG_PACKAGE_'+pkg),'n',pkg)

    def test_reusable_workflow_and_pinned_onu_feed_are_preserved(self):
        text=(ROOT/'.github/workflows/build-ponwrt.yml').read_text(encoding='utf-8')
        self.assertIn('  workflow_call:',text)
        self.assertIn('OpenWrt_ONU_CONFIG.git^3cb13560459f1d51136dac662baa1f399028b2b4',text)
        self.assertIn('scripts/check-required-packages.sh',text)
        self.assertIn("PREBUILT_HOST: ${{ inputs.prebuilt_host == 'true' && 'true' || 'false' }}",text)

    def test_no_new_scheduled_build_and_no_duplicate_openclash_fetch(self):
        for name in ('warm-cache.yml','cache-clean.yml'):
            text=(ROOT/'.github/workflows'/name).read_text(encoding='utf-8')
            self.assertNotIn('\n  schedule:',text)
        text=(ROOT/'diy-part1.sh').read_text(encoding='utf-8')
        self.assertIn('scripts/fetch-required-packages.sh',text)
        self.assertIn('ADD_OPENCLASH=false',text)

if __name__=='__main__':
    unittest.main()
