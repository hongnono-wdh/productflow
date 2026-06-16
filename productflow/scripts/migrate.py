#!/usr/bin/env python3
"""ProductFlow 数据迁移钩子 —— 自动更新（git pull 拉到新版后）由 server 的 /api/update 调用。

数据保留：用户的项目数据在 skill **之外**（全局 `~/.productflow/` 的注册表/pending/secrets，以及各项目
`~/code/<slug>/.productflow/`），git pull 只动 skill 代码、碰不到这些——所以**升级天然保留数据**。

本脚本只负责"版本升级时需要的数据格式迁移"：当前各数据文件格式未变 → no-op。
将来若改了数据格式，在这里按版本加**幂等、先备份**的迁移步骤（见下方范式注释）。
"""
import os
import sys

PF_HOME = os.path.expanduser("~/.productflow")


def main() -> int:
    # 目前没有需要迁移的数据格式变更。
    #
    # 将来加迁移的范式（每步要幂等 + 先备份，且只在检测到旧格式时才动）：
    #   import glob, json, shutil
    #   for f in glob.glob(os.path.join(PF_HOME, "projects", "*.json")):
    #       reg = json.load(open(f)); sp = os.path.join(reg["path"], ".productflow", "state.json")
    #       st = json.load(open(sp))
    #       if 需要迁移(st):
    #           shutil.copy(sp, sp + ".bak")        # 先备份
    #           迁移(st); json.dump(st, open(sp, "w"), ensure_ascii=False, indent=2)
    #
    # 不兼容的旧版项目（如 5 阶段老数据）走操作台的不兼容横幅提示重建，不在此强行迁移。
    print("migrate: 无需迁移（数据格式未变，用户项目数据已原样保留）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
