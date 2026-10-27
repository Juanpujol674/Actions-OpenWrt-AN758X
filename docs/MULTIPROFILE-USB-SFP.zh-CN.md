# 多机型 USB-SFP 镜像清单

适用于 Actions → **PonWrt Multi-profile (AN7581 + AN7583)**。
选择 `target=both`，需要 ONU 时勾选 `use_onu`；需要发布时勾选 `publish_release`。
本次不改变 ONU 开关、源码仓库、工具链、编译并行数或缓存策略。

## 本次修复

旧多机型流程只选择 AN7581 的 9 个机型和 AN7583 的 2 个机型；未选择的机型不会编译，发布脚本也不会检查它们。
现在编译、defconfig 后检查、产物整理共用 `scripts/device_profiles.py` 清单。
AN7581 包含 14 个升级镜像，AN7583 保持 2 个。

| 平台 | 机型 / 变体 | 升级格式 |
| --- | --- | --- |
| AN7581 | fiberhome_hg5382a | .itb |
| AN7581 | fiberhome_hg5585f-ct | .itb |
| AN7581 | fiberhome_hg5585f-ct-usb-sfp（新增） | .itb |
| AN7581 | fiberhome_hg5585f-cu | .itb |
| AN7581 | fiberhome_hg5585f-cu-usb-sfp（新增） | .itb |
| AN7581 | gemtek_w1700k-ubi（补选） | .itb |
| AN7581 | gemtek_xg2010g | .itb |
| AN7581 | h3c_hm2004-du（补选） | .itb |
| AN7581 | nokia_xg-040g-md-ubi | .itb |
| AN7581 | nokia_xg-040g-md-ubi-usb-sfp（新增） | .itb |
| AN7581 | nokia_xg-040g-tf-ubi | .itb |
| AN7581 | unionman_ung00a | .itb |
| AN7581 | znxt_zn504xg-d | .itb |
| AN7581 | znxt_zn515xg-d | .itb |
| AN7583 | nokia_xg-040g-mf | .bin |
| AN7583 | nokia_xg-040g-mf-ubi | .itb |

## 两种镜像的区别

HG5585F CT/CU、040G-MD 的 USB-SFP 是上游已有的独立设备树变体，涉及 USB SerDes 的复用。
增加 USB 网卡驱动或改固件文件名不能替代对应设备树。本次直接选中上游 profile，软件组件沿用同型号普通版。

W1700K 在参考 Release 中的另一个 `.itb` 是 `chainload-uboot` 引导加载器，不是 USB-SFP 版；本工作流仍只发布 sysupgrade 镜像，不混入引导加载器或 recovery 镜像。
W1700K 没有本地机型配置，使用现有配置的共同软件组件，由上游机型定义提供其 MT7996、PHY 等板级依赖，不借用其他机型的设备树。

040G-MF 的普通 `.bin` 和 UBI `.itb` 对应不同分区布局，两个 profile 都保留。
当前 pbs05/ponwrt 没有独立的 W1700K、XG2010G、HM2004、040G-TF/MF `usb-sfp` profile，不生成虚构型号。

HM2004 使用现有本地配置中的公开软件组件。多机型工作流已经设置 `ADD_FTTR=false`，因此剔除私有 FMCS/FTTR 套件及配置项，防止在每机型 rootfs 安装不存在的软件包。原单机型工作流的私库支持不受影响。

## 检查与使用

- 合并前测试：`python3 -m unittest discover -s tests -v`。
- 选定 profile 在克隆的上游 `target/linux/airoha/image/<soc>.mk` 中不存在时，提前报错。
- `make defconfig` 后检查每一个 profile 是否还被选中。
- 发布前要求清单中的每个 sysupgrade 都存在且非空；缺少任何一个（包括 USB-SFP）就阻止部分发布。
- 本地回归测试不是完整云端编译；合并后先在 Actions 运行需要的平台，确认新镜像产出，再按型号分别验证硬件。

核对基座：[pbs05/ponwrt 03c1345 的 AN7581 镜像定义](https://github.com/pbs05/ponwrt/blob/03c134544714617e196dd399c85ebb90fb6eefa1/target/linux/airoha/image/an7581.mk)。
参考清单：[VIKINGYFY 2026-10-27 发布](https://github.com/VIKINGYFY/OpenWRT-CI/releases/tag/AIROHA-VIKINGYFY-owrt-26.10.27-08.38.44)。
