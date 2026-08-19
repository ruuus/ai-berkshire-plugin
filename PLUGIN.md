# AI Berkshire Codex Plugin 维护与安装指南

本仓库将上游 [xbtlin/ai-berkshire](https://github.com/xbtlin/ai-berkshire) 的 `main` 分支转换为 Codex marketplace 插件。上游仓库是业务工作流与共享工具的唯一来源；本分支只维护打包适配。

## 分支策略

- `main`：完整镜像上游项目，不放插件专属修改。
- `codex-plugin`：精简发布分支，只保存 marketplace、插件产物、生成/验证/发布工具和文档。
- `UPSTREAM.lock.json`：记录插件产物对应的完整上游 commit、提交时间和文件数量。
- `plugins/ai-berkshire/skills/` 与 `plugins/ai-berkshire/tools/`：生成目录，禁止手工编辑。
- `plugin-packaging/overlay/`：只保存无法直接从上游复制的 Codex 或跨平台适配。

> [!IMPORTANT]
> 不要把 `main` 合并进 `codex-plugin`。同步器会从 `main`、`upstream/main` 或独立 checkout 创建临时源码树，只把生成后的插件产物带回本分支。

## 从最新上游生成插件

### 方式一：使用同一仓库的 `main` 分支

首次配置上游 remote：

```bash
git remote add upstream https://github.com/xbtlin/ai-berkshire.git
git fetch upstream
```

以后更新：

```bash
git switch main
git fetch upstream
git merge --ff-only upstream/main

git switch codex-plugin
```

不要执行 `git merge main`。先修改 `plugins/ai-berkshire/.codex-plugin/plugin.json` 中的 SemVer 版本，然后生成：

```bash
python3 plugin-packaging/sync_from_upstream.py --upstream-ref main
python3 plugin-packaging/sync_from_upstream.py --check --upstream-ref main
python3 plugin-packaging/validate.py
```

也可以直接以已抓取的 `upstream/main` 为来源：

```bash
git fetch upstream
python3 plugin-packaging/sync_from_upstream.py --upstream-ref upstream/main
python3 plugin-packaging/sync_from_upstream.py --check --upstream-ref upstream/main
python3 plugin-packaging/validate.py
```

同步器会创建 detached 临时 worktree，结束时自动移除。`codex-plugin` 的工作树不需要保存任何上游 `skills/`、`codex-skills/`、`tools/` 或 `scripts/` 目录。

### 方式二：使用独立上游 checkout

```bash
git clone https://github.com/xbtlin/ai-berkshire.git ../ai-berkshire-upstream
git -C ../ai-berkshire-upstream pull --ff-only

python3 plugin-packaging/sync_from_upstream.py \
  --source-dir ../ai-berkshire-upstream
python3 plugin-packaging/sync_from_upstream.py \
  --check \
  --source-dir ../ai-berkshire-upstream
python3 plugin-packaging/validate.py
```

`--source-dir` 必须指向干净 Git checkout 的根目录。同步器会拒绝存在未提交 canonical 文件修改的源码树，但不会要求其中已提交的 `codex-skills/` 已经与 `skills/` 同步。它会把 canonical skills、现有 Codex-only skill 和上游生成脚本复制到独立临时目录，清理旧派生 skill，再依次执行生成与 `--check`。整个过程不会写回该 checkout。

## 同步器执行内容

1. 校验上游 canonical 路径没有未提交修改，并记录当前完整 commit。
2. 在隔离临时目录从 `skills/*.md` 重新生成派生 Codex skills，同时保留手写的 Codex-only skill。
3. 对临时生成结果再次运行上游生成器的 `--check`。
4. 复制 21 个 Codex skills、共享 `tools/` 和上游 `LICENSE`。
5. 把技能中的工具路径改为 `{AI_BERKSHIRE_ROOT}/tools/`。
6. 应用 `ashare_data.py` 与 `xueqiu_scraper.py` 的跨平台适配。
7. 加入 `plugin_doctor.py`、`NOTICE` 和可选依赖文件。
8. 生成 `plugins/ai-berkshire/BUILD-INFO.json` 与根目录 `UPSTREAM.lock.json`。

如果上游修改了被适配代码的上下文，同步器会失败并要求人工复核，不会静默套用补丁。

## 自动校验

`.github/workflows/plugin-validate.yml` 会在 `codex-plugin` 的每次 push 和 pull request 上运行。工作流读取 `UPSTREAM.lock.json`，从 `xbtlin/ai-berkshire` 独立检出锁定提交，然后执行：

```bash
python3 plugin-packaging/sync_from_upstream.py --check --source-dir .upstream/ai-berkshire
python3 plugin-packaging/validate.py
```

校验器同时检查：

- manifest、marketplace、SemVer 和技能数量。
- 构建信息与上游锁文件一致。
- 技能引用、插件根路径和工具可移植性。
- Python 工具语法、关键工具 `--help` 与插件诊断。
- 顶层文件只来自精简发布分支白名单，防止误合并完整上游树。

## Git sparse 在线安装

公开仓库无需 GitHub Token 或 SSH Key：

```bash
codex plugin marketplace add ruuus/ai-berkshire-plugin \
  --ref codex-plugin \
  --sparse .agents/plugins \
  --sparse plugins/ai-berkshire
codex plugin add ai-berkshire@ai-berkshire-plugin
```

检查：

```bash
codex plugin marketplace list
codex plugin list
```

升级：

```bash
codex plugin marketplace upgrade ai-berkshire-plugin
codex plugin add ai-berkshire@ai-berkshire-plugin
```

只卸载插件：

```bash
codex plugin remove ai-berkshire@ai-berkshire-plugin
```

同时移除 marketplace：

```bash
codex plugin marketplace remove ai-berkshire-plugin
```

## Release 离线安装

从 [GitHub Releases](https://github.com/ruuus/ai-berkshire-plugin/releases) 下载同一版本的 ZIP 或 tar.gz 与 `SHA256SUMS`。校验后解压；Codex CLI 不能直接安装压缩包。

```bash
codex plugin marketplace add /absolute/path/to/ai-berkshire-plugin-vX.Y.Z
codex plugin add ai-berkshire@ai-berkshire-plugin
```

升级离线安装时，下载新版到新目录并重新绑定：

```bash
codex plugin remove ai-berkshire@ai-berkshire-plugin
codex plugin marketplace remove ai-berkshire-plugin
codex plugin marketplace add /absolute/path/to/new/ai-berkshire-plugin-vX.Y.Z
codex plugin add ai-berkshire@ai-berkshire-plugin
```

确认新版可用后可删除旧解压目录。`marketplace upgrade` 只刷新 Git marketplace，不适用于本地解压目录。

## 构建与发布 Release

本地构建：

```bash
python3 plugin-packaging/build_release.py \
  --output-dir dist \
  --expected-version 0.2.1
```

输出：

```text
dist/ai-berkshire-plugin-v0.2.1.zip
dist/ai-berkshire-plugin-v0.2.1.tar.gz
dist/SHA256SUMS
```

发布前确保 manifest、`UPSTREAM.lock.json` 和标签版本一致，然后提交 `codex-plugin` 并推送 `vX.Y.Z` 标签。Release 工作流会按锁定上游提交重新校验并自动上传三个资产。

## 安装后验证与可选依赖

新建 Codex 线程，在 `/plugins` 中确认插件启用，然后测试：

```text
使用 ai-berkshire:investment-team 研究一家上市公司
```

本地诊断：

```bash
python3 plugins/ai-berkshire/tools/plugin_doctor.py
```

只有雪球抓取需要额外依赖：

```bash
python -m pip install -r <插件安装目录>/requirements-optional.txt
python -m playwright install chromium
```

`WARN playwright` 只表示可选依赖未安装，不影响核心研究、估值和报告审计工具。

## ChatGPT 网页版

本仓库的 marketplace 命令面向 Codex CLI 与支持插件的 Codex/ChatGPT 客户端环境，不能把 GitHub 仓库或 Release 压缩包直接安装到普通 ChatGPT 网页会话。网页版可用性和分发方式以当前账号、工作区及 OpenAI 插件发布界面为准。

## 许可与免责声明

插件分发须保留 `LICENSE` 与 `NOTICE`。本项目仅供学习和研究，不构成投资建议。
