#!/usr/bin/env python3
"""Prepare timestamped sysupgrade filenames and a release body from manifests."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import re


def packages_from_manifest(path):
    packages = {}
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        match = re.fullmatch(r'(\S+)\s+-\s+(.+)', line.strip())
        if match:
            packages[match[1]] = match[2]
    return packages


def prepare(images, stage, soc, metadata, timestamp=None):
    now = timestamp or datetime.now(timezone(timedelta(hours=8)))
    stamp = now.strftime('%Y.%m.%d-%H.%M.%S')
    display_time = now.strftime('%Y-%m-%d %H:%M:%S UTC+08:00')
    staged = sorted(p for p in stage.iterdir() if p.is_file())
    if not staged or any(not re.search(r'-squashfs-sysupgrade\.(itb|bin)$', p.name) for p in staged):
        raise ValueError('Stage must contain only the complete sysupgrade image set')
    manifests = sorted(images.glob('*.manifest'))
    package_sets = [packages_from_manifest(p) for p in manifests]
    plugins = sorted({name for pkgs in package_sets for name in pkgs
                      if name.startswith(('luci-app-', 'luci-theme-'))})
    kernels = sorted({m[0] for pkgs in package_sets
                      if (m := re.findall(r'^\d+\.\d+(?:\.\d+)?', pkgs.get('kernel', '')))})
    # Keep metadata separate from the sysupgrade-only upload directory.
    metadata.mkdir(parents=True, exist_ok=True)
    destinations = [(src, src.with_name(src.name.replace('-squashfs-sysupgrade.',
                    f'-{stamp}-squashfs-sysupgrade.'))) for src in staged]
    if any(dst.exists() for _, dst in destinations):
        raise FileExistsError('Timestamped image already exists')
    rows = []
    for src, dst in destinations:
        with src.open('rb') as image:
            digest = hashlib.file_digest(image, 'sha256').hexdigest()
        rows.append((dst.name, digest))
    for src, dst in destinations:
        src.rename(dst)
    platform = soc.upper()
    body = [
        '这是一个平台固件包，内含多个设备！',
        '请注意选择与你的设备型号、闪存布局一致的固件！', '',
        f'配置：{platform}（多机型）', '平台：airoha', f'子平台：{soc}',
        f'构建完成时间：{display_time}', '',
        '登录地址：192.168.1.1', '登录密码：无（首次启动后请设置密码）',
        '以上为全新刷写的默认设置；保留配置升级时沿用原设置。', '',
        'WIFI名称：不适用（AN7583 无 Wi-Fi）' if soc == 'an7583' else
        'WIFI名称：按机型及首次启动配置生成',
        'WIFI密码：不适用' if soc == 'an7583' else 'WIFI密码：以设备实际配置为准', '',
        '内核版本：' + (' / '.join(kernels) or '未从产物清单读取到'),
        '插件列表（产物清单中 LuCI 应用和主题的并集，具体机型可能不同）：',
        ' '.join(plugins) or '未从产物清单读取到', '',
        'ONU 界面：' + ('清单包含 luci-app-onu' if 'luci-app-onu' in plugins else
                         '产物清单未发现 luci-app-onu'), '',
        '仅包含 sysupgrade 升级镜像，不包含首次刷机或救砖镜像。',
    ]
    if soc == 'an7583':
        body += ['普通版 nokia_xg-040g-mf 使用 .bin；UBI 版 nokia_xg-040g-mf-ubi 使用 .itb，二者不可混刷。',
                 '测试记录：此前版本的 UBI 镜像已由用户刷机验证；本次新构建及其他机型仍需分别验证。']
    body += ['', '镜像 SHA256：', '', '```text'] + [f'{digest}  {name}' for name, digest in rows] + ['```', '']
    (metadata / 'release-notes.md').write_text('\n'.join(body), encoding='utf-8')
    return stamp, f'PonWrt {platform} {stamp}'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('soc', choices=('an7581', 'an7583'))
    parser.add_argument('--images', required=True, type=Path)
    parser.add_argument('--stage', required=True, type=Path)
    parser.add_argument('--metadata', required=True, type=Path)
    parser.add_argument('--github-output', required=True, type=Path)
    args = parser.parse_args()
    stamp, title = prepare(args.images, args.stage, args.soc, args.metadata)
    with args.github_output.open('a', encoding='utf-8') as output:
        output.write(f'stamp={stamp}\ntitle={title}\n')
    print(title)


if __name__ == '__main__':
    main()
