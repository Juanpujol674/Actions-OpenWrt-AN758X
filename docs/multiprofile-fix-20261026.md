# AN758X 全家桶失败修复（2026-10-26）

该补丁依据用户提供的 `logs_109079436586` 两个 Job 原始日志制作。两个上传 ZIP 的内容一致：

- AN7581 在 `make-multiprofile-config.py` 即报 `ERROR: configurations disagree on global settings`，主要是不同设备的 `CONFIG_PACKAGE_*` 差异；旧脚本会把例如无线驱动的 `y` / `n` 差异判为不可合并。
- AN7583 配置和 `make defconfig` 通过；在 `make -j4` 中 `package/feeds/packages/yq failed to build`。日志没有包含 yq 实际编译命令和失败原因，因此不能认定是 Go 内存问题或 ONU 开关问题。

## 本次修正

1. 更换 `scripts/make-multiprofile-config.py`：所有机型都需要的包仍设 `y`；只有部分机型需要的包设 `m`，只通过 `CONFIG_TARGET_DEVICE_PACKAGES_...="pkg ..."` 添加到对应机型的固件。保留 `CONFIG_TARGET_PER_DEVICE_ROOTFS=y`，避免将 MT7915 驱动装进 Nokia 的设备固件。对非软件包的系统设置冲突继续报错，避免误改闪存分区等属性。
2. 解析 `.config` 时去掉 `=y  # 中文注释` 一类行内注释（旧代码曾将注释误读成 Kconfig 值）。
3. `scripts/verify-multiprofile.sh` 加入 per-device rootfs 验证。
4. 新增 `scripts/build-with-diagnostics.sh`：降低并发为 2，Go 使用 `GOMAXPROCS=2` 和 `GOFLAGS=-p=1` 以控制并发峰值；若失败，保存 `.ci-logs/build.log`、错误摘要、原始编译日志摘录；如果定位到 yq，会用 `-j1 V=sc` 对其单独诊断。**这会改善诊断，但不保证能修复尚未查明原因的 yq 构建错误。**
5. 全家桶工作流新增失败日志 Artifact 和 `use_onu` 开关，保留 `publish_release=false` 作为首次测试默认值。

## 导入注意

此 ZIP 是**完整文件版**，不是一个可独立在浏览器自动建立 PR 的链接。如果你之前修改过工作流（例如添加了其他自定义 `workflow_dispatch` 选项），请先比较差异，保留你的自定义内容。不要盲目覆盖其他 DIY 文件、缓存机制或单机型工作流。

- 建议在 Fork 的新分支 `fix/multiprofile-and-build-logs` 上替换 ZIP 中 `.github/workflows/firmware-multiprofile.yml` 与同名 `scripts/` 文件。
- 完成 PR 后先运行 `target=an7581, use_onu=false, publish_release=false`；再运行 AN7583 两种 ONU 选项。观察 Artifacts 是否出现 `PonWrt-an7583-diagnostics`。
- 如果仍因 yq 失败，请**下载 `PonWrt-an7583-diagnostics`，重点看 `yq-verbose.log`**，之后才能依据真实错误确定是否要改 Go 工具链、包版本、下载源或编译条件。
- 单机型工作流也可在原 `working-directory: openwrt` 的编译 step 中把 `make -j4` 改为 `bash "$GITHUB_WORKSPACE/scripts/build-with-diagnostics.sh" 2`，并在失败时上传 `openwrt/.ci-logs/*`。没有获取原单机型 workflow 全文，因此未贸然改写它。

## 不能提前宣称通过的测试

Python 合并脚本可以进行模拟测试，workflow 可进行 YAML 语法检查；本地没有完整 PonWrt 源码及已编译工具链，不可能验证成品固件能正常刷写。请保留旧版编译和已刷写的备份。
