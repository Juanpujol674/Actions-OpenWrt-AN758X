# yq 构建失败：下载清理误删 Go 源码

`logs_109362401039.zip` 中 AN7583 在 yq 4.53.6 编译阶段失败。串行诊断显示：

- `github.com/mattn/go-isatty@v0.0.20`：`build constraints exclude all Go files`。
- `go-cty/cty/internal/graphemes`、`go-cmp/cmp/internal/flags`、`pkg/diff/intern` 缺失。

下载后执行的递归 `find dl -type f -size -1024c -delete` 会进入
`dl/go-mod-cache`，删除合法的小型源码和模块元数据。上游 go-isatty
v0.0.20 的 Linux 实现 `isatty_tcgets.go` 小于 1 KB，也会被删除。
因此再次降低并发或修改 Go 版本不能解决这个清理错误。

本次修复：

1. 多机型工作流与单机型工作流的三个清理点均限制为 `dl` 顶层文件。
2. 两个工作流的下载缓存键切换到 `ponwrt-dl-v2-`，单机型的恢复前缀
   同步更新，避免恢复此前已损坏的模块缓存。
3. 回归测试执行工作流中的真实 GNU find 命令，确认嵌套 Go 源码与元数据
   保留、1 KB 下载包保留、顶层小型残留删除。

保留现有 ONU 配置、发布命名和失败诊断。日志中的 qt5/squeezelite
递归依赖提示之后仍完成了配置生成；它们并非本次终止构建的 yq 错误。

合并后先运行多机型工作流：`target=an7583`、`use_onu=false`、
`publish_release=false`。首次运行采用新的下载缓存，可能需要重新下载。
本地测试验证了清理行为，完整 OpenWrt/yq 交叉编译仍需 GitHub Actions 验证。
