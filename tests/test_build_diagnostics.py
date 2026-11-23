"""Exercise failure diagnostics with a fake make, without compiling firmware."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
if not BASH and Path("C:/Program Files/Git/bin/bash.exe").exists():
    BASH = "C:/Program Files/Git/bin/bash.exe"


@unittest.skipUnless(BASH, "bash is required")
class BuildDiagnosticsTests(unittest.TestCase):
    def run_build(self, success=False):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / "bin").mkdir()
            fake = work / "bin/make"
            fake.write_text("""#!/usr/bin/env bash
printf '%s\\n' "$*" >> calls.txt
if [ "${FAKE_SUCCESS:-}" = 1 ]; then exit 0; fi
if [ "$*" = '-j1 V=sc target/install' ]; then
  echo 'Image HG5585F is too big: diagnostic sentinel'
  exit 3
fi
mkdir -p logs/target/linux
printf 'Image exceeds partition limit\\n' > logs/target/linux/install.txt
echo 'ERROR: target/linux failed to build.'
exit 2
""", encoding="utf-8", newline="\n")
            fake.chmod(0o755)
            env = os.environ.copy()
            env["DIAGNOSTIC_SCRIPT"] = (ROOT / "scripts/build-with-diagnostics.sh").as_posix()
            env["FAKE_SUCCESS"] = "1" if success else "0"
            result = subprocess.run(
                [BASH, "-c", 'export PATH="$PWD/bin:$PATH"; bash "$DIAGNOSTIC_SCRIPT" 2'],
                cwd=work, env=env, capture_output=True, text=True,
            )
            calls = (work / "calls.txt").read_text().splitlines()
            files = {str(p.relative_to(work)): p.read_text() for p in (work / ".ci-logs").rglob("*") if p.is_file()}
            return result, calls, files

    def test_image_failure_is_replayed_and_original_exit_is_preserved(self):
        result, calls, files = self.run_build()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(calls, ["-j2", "-j1 V=sc target/install"])
        self.assertIn("diagnostic sentinel", result.stdout)
        self.assertTrue(any("target-logs" in p and "partition limit" in text for p, text in files.items()))
        self.assertTrue(any("target-install-verbose.log" in p for p in files))

    def test_success_does_not_replay_or_change_result(self):
        result, calls, files = self.run_build(success=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["-j2"])
        self.assertFalse(any("target-install-verbose.log" in p for p in files))
