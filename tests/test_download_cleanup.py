"""Exercise the actual workflow cleanup commands against a Go module cache."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DownloadCleanupTests(unittest.TestCase):
    def test_workflows_preserve_module_sources_and_valid_archives(self):
        find = os.environ.get('GNU_FIND') or shutil.which('find')
        if not find:
            self.skipTest('GNU find is required')
        for workflow in ('firmware-multiprofile.yml', 'build-ponwrt.yml'):
            text = (ROOT / '.github/workflows' / workflow).read_text(encoding='utf8')
            commands = [line.strip() for line in text.splitlines()
                        if line.strip().startswith('find dl ')]
            self.assertTrue(commands, workflow)
            for command in commands:
                with self.subTest(workflow=workflow, command=command), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    dl = root / 'dl'
                    module = dl / 'go-mod-cache/github.com/mattn/go-isatty@v0.0.20'
                    module.mkdir(parents=True)
                    source = module / 'isatty_tcgets.go'
                    source.write_bytes(b'//go:build linux\npackage isatty\n')
                    metadata = dl / 'go-mod-cache/cache/download/example/@v/v1.0.0.mod'
                    metadata.parent.mkdir(parents=True)
                    metadata.write_bytes(b'module example\n')
                    damaged = dl / 'truncated.tar.xz'
                    damaged.write_bytes(b'error page')
                    empty = dl / 'empty.tar.gz'
                    empty.touch()
                    archive = dl / 'valid.tar.xz'
                    archive.write_bytes(b'x' * 1024)
                    args = shlex.split(command)
                    args[0] = find
                    subprocess.run(args, cwd=root, check=True, capture_output=True, text=True)
                    self.assertEqual(source.read_bytes(), b'//go:build linux\npackage isatty\n')
                    self.assertEqual(metadata.read_bytes(), b'module example\n')
                    self.assertTrue(archive.exists())
                    self.assertFalse(damaged.exists())
                    self.assertFalse(empty.exists())


if __name__ == '__main__':
    unittest.main()
