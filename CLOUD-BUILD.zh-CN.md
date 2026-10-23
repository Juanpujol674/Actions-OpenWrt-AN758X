# 云编译全家桶使用说明

## 替换方法

本目录只包含新增或修改的文件。把 `.github`、`configs`、`scripts`、根目录文件按相同路径合并进 GitHub 仓库，保留仓库里其他文件，提交到 master。
不要把 D 盘外层的 Actions-OpenWrt-AN758X 文件夹当作仓库子目录上传。
Windows 文件管理器请显示隐藏项目，否则容易漏掉 `.github` 和 `.gitattributes`。

推荐：GitHub Desktop 克隆自己的仓库，然后把 replacement 中的全部内容覆盖到本地克隆目录，检查 Changes，Commit，再 Push origin。不要直接上传 ZIP 到 GitHub：ZIP 需要先解压。

## 首次运行

1. 在自己的 Fork → Actions，启用工作流；Settings → Actions → General 确认允许 Actions 运行。
2. 建议先选 `Build PonWrt (Airoha AN758x PON)` → Run workflow，选择实际机型，source 保持 pbs05/ponwrt，private_repo 保持 none，scope 保持 firmware。
3. 单机型成功后，运行 `Build all devices (full bundle)`。它会依次分批处理 configs 中现有的 12 个机型，覆盖 AN7581 和 AN7583，每次最多并行 2 个任务。一台失败不取消其他机型。
4. 成功产物在该次 Actions 的 Artifacts 和 Releases 下载；Release 按机型滚动更新。型号必须与自己的硬件和分区格式一致。

批量入口与原入口的 profile=all 不同：原 all 是指定 SoC 的通用配置；新入口明确枚举全部 12 个机型，包括 H3C HM2004-DU。
免费托管 runner 的单任务时间上限仍然存在，首次含 Go/Rust 工具链的冷构建可能超时。并行数为 2 是默认折中，可编辑 build-all.yml 的 max-parallel。

## 每个机型默认组件

- 华为 5G USB 网卡：kmod-usb-net、kmod-usb-net-rndis、kmod-usb-net-cdc-ether、kmod-usb-net-cdc-ncm、kmod-usb-net-huawei-cdc-ncm、kmod-usb-wdm。
- luci-app-openclash、luci-app-nikki、luci-app-momo。
- luci-app-onu 及 airoha-pond、airoha-ponctl、airoha-pon-debug，ONU 简体中文翻译。

配置已经写入全部 14 个 config 文件（12 个机型、2 个 SoC 通用配置）。defconfig 后逐项检查必需组件，缺失直接报错，避免交付缺组件固件。
三个代理界面都安装；使用时只启用其中一个，配置订阅/节点后再启动，避免同时接管 DNS 和透明代理规则。
OpenClash 的 LuCI 包不等于已预置运行核心，首次使用需在插件内下载核心、配置订阅；Nikki 自带的 mihomo-meta 在云端编译，Momo 的 sing-box 使用 packages feed。
USB 驱动只提供网卡识别能力，实际联网还需要对应 USB 模式与 WAN/DHCP 配置，不包含 SIM/APN 自动配置。

## ONU 集成方式

将原 pon_userspace feed 整体替换为 https://github.com/naoki66/OpenWrt_ONU_CONFIG ，同时更新前端与用户态后端。
禁用 luci-app-pon 与 luci-app-iptv 及其旧中文包；它们的功能由 luci-app-onu 接管，避免网络配置/脚本冲突。
PON 概览卡片也来自同一 ONU 源，避免重复定义。
包含该仓库 patches/firewall4/010-fw4-zone-device-flowtable.patch，安装到源码 firewall4 的 patches 目录，用于 zone device 的 VLAN/PPPoE 流量卸载。已对当前 pbs05/ponwrt 所引用的 firewall4 提交验证补丁能应用。
ONU 硬件身份、认证、上网、IPTV、语音功能保留上游行为；页面可用不表示所有板型的所有业务都经过实机测试。没有预置 SN、LOID、密码或运营商参数。

## 私有 FTTR

原项目 H3C 的 FMCS/FTTR 后端依赖作者的私有仓库，本次默认 private_repo=none，因此不包含该私有 FTTR 套件。
这不影响你列出的 USB/代理/ONU 组件。若已有该私库访问权，可在单机型入口选择对应私库并按原项目方式配置 Secrets。
批量需要私有 FTTR 时，修改 build-all.yml 的 private_repo，并配置有权读取该仓库的凭证。

## 后续定时编译

build-all.yml 已保留注释的 schedule 示例，当前不会定时编译固件。
示例 `0 20 * * 0` 是 UTC 周日 20:00，即北京时间周一 04:00。确定时间后取消 schedule 两行注释并修改 cron。
定时任务读取默认分支，需将修改提交到 master。原 cache-keepalive.yml 的定时任务只是缓存检查，不会编译固件。

## 更新和维护

ONU、OpenClash、Nikki、Momo 固定到本次检查的提交，减少后续上游变化带来的不确定性；OpenWrt 基座与其他 feeds 仍跟随选定分支。
升级 ONU 时修改 build-ponwrt.yml 的 pon_userspace URL 后面的提交号，同时检查 firewall4 补丁兼容性。
升级三个代理包时修改 scripts/fetch-required-packages.sh 中对应提交号。
新增机型时新增 configs/<profile>.config，并在 build-all.yml 的 matrix.profile 添加同名 profile；沿用现有配置中的 Required bundle 段。
原入口为兼容输入数量限制保留 10 个手动参数；加密三个开关、SSH 仍可通过可复用工作流调用的输入指定，默认关闭。

## 验证范围

已检查两个修改/新增的 Actions 工作流（actionlint）、新增 shell 脚本语法、所有机型必需包配置、矩阵与机型数量、Git 差异空白，以及 firewall4 补丁对基座所用源码的适用性。
尚未在 GitHub Actions 执行完整交叉编译，未在实机刷写测试。最终是否编译成功，以首次云端运行日志为准；不能把本地静态校验视作完整编译通过。
