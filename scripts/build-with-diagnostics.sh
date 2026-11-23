#!/usr/bin/env bash
# Run inside the openwrt tree. Usage: build-with-diagnostics.sh [jobs]
set -euo pipefail
jobs="${1:-2}"
case "$jobs" in ''|*[!0-9]*) echo "Invalid jobs count: $jobs" >&2; exit 2;; esac
mkdir -p .ci-logs
log=".ci-logs/build.log"
# Save full low-noise log and stream it to Actions.
set +e
make -j"$jobs" 2>&1 | tee "$log"
status=${PIPESTATUS[0]}
set -e
if [ "$status" -eq 0 ]; then
  echo "Build completed successfully"
  exit 0
fi

echo "::error::PonWrt build failed (exit $status); check uploaded CI diagnostics."
{
  echo "===== first error / likely failures ====="
  grep -Ein 'error:|fatal:|failed to build|no space left|signal: killed|out of memory|cannot find|no rule to make' "$log" | tail -n 140 || true
  echo "===== last 160 build lines ====="
  tail -n 160 "$log"
} | tee .ci-logs/error-summary.txt
# OpenWrt may save the actual compiler diagnostic in logs/ rather than stdout.
if [ -d logs ]; then
  find logs -type f -name '*.txt' | grep -Ei '/(yq|golang)/|compile' | head -n 80 > .ci-logs/possible-compiler-logs.txt || true
  find logs -type f \( -name '*.txt' -o -name '*.log' \) -print0 | \
    xargs -0 -r grep -IlEi 'error:|fatal:|signal: killed|no space left|too big|too large|cannot find|not found|failed|Error [0-9]' 2>/dev/null | \
    head -n 30 > .ci-logs/error-log-paths.txt || true
  while IFS= read -r file; do
    echo "===== $file =====" >> .ci-logs/compiler-errors.txt
    tail -n 120 "$file" >> .ci-logs/compiler-errors.txt
  done < .ci-logs/error-log-paths.txt
fi

# Image creation errors are normally hidden by OpenWrt's low-noise output.
# Re-run only image installation, using the already-built kernel and packages.
if grep -Fq 'ERROR: target/linux failed to build' "$log"; then
  echo '::group::Reproduce image installation failure (serial verbose; max 10 minutes)'
  set +e
  timeout 600 make -j1 V=sc target/install > .ci-logs/target-install-verbose.log 2>&1
  retry_status=$?
  set -e
  echo "Diagnostic target/install exit: $retry_status (original build exit: $status)"
  tail -n 240 .ci-logs/target-install-verbose.log
  echo '::endgroup::'
fi
# Keep native image/rootfs logs too: image-size and package-install errors do
# not necessarily contain a C compiler 'error:' marker.
if [ -d logs/target ]; then
  cp -R logs/target .ci-logs/target-logs
fi
if [ -d logs/package/install ]; then
  cp -R logs/package/install .ci-logs/package-install-logs
fi
{
  echo '===== remaining disk space ====='
  df -h .
  echo '===== image output sizes ====='
  du -h bin/targets/airoha/*/* 2>/dev/null || true
} > .ci-logs/image-environment.txt

if grep -Eq 'package/feeds/packages/yq failed to build' "$log"; then
  echo '::group::Reproduce yq failure with make -j1 V=sc (max 10 minutes)'
  # May succeed if the initial failure was a race. Preserve original failure.
  timeout 600 make -j1 V=sc package/feeds/packages/yq/compile \
    > .ci-logs/yq-verbose.log 2>&1 || true
  tail -n 180 .ci-logs/yq-verbose.log
  echo '::endgroup::'
fi
exit "$status"
