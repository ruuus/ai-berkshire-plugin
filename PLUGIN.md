# AI Berkshire Codex Plugin

本分支把上游 [xbtlin/ai-berkshire](https://github.com/xbtlin/ai-berkshire)
的当前 `main` 制作为可由 Codex marketplace 安装的插件。上游研究流程仍是唯一业务
来源；`plugins/ai-berkshire/` 由同步脚本生成，不在其中手工维护 21 份 skill 副本。

## 仓库约定

- `main`：跟踪上游项目，不放插件专属改动。
- `codex-plugin`：维护插件 manifest、marketplace、同步器、便携性覆盖层和生成产物。
- `UPSTREAM.lock.json`：记录本次插件对应的上游完整 commit。
- `plugin-packaging/overlay/`：只放确实不能直接从上游复制的 Codex/跨平台文件。
- `plugins/ai-berkshire/skills/` 和 `tools/`：生成目录；禁止手工编辑。

当前插件在上游 Codex skills 的基础上提供两类适配：

1. 所有共享工具都通过 `{AI_BERKSHIRE_ROOT}/tools/` 定位，不依赖任务当前目录。
2. `ashare_data.py` 支持 PATH 中的 `curl`/`curl.exe` 并回退标准库；
   `xueqiu_scraper.py` 使用系统临时目录，且 Playwright 仅在实际爬取时才要求安装。

## 从最新上游更新

第一次设置 fork：

```bash
git remote add upstream https://github.com/xbtlin/ai-berkshire.git
git fetch upstream
```

每次更新：

```bash
git switch main
git fetch upstream
git merge --ff-only upstream/main

git switch codex-plugin
git merge --no-edit main
```

随后更新
`plugins/ai-berkshire/.codex-plugin/plugin.json` 的 SemVer 版本，再执行：

```bash
python3 scripts/sync-codex-skills.py --check
python3 plugin-packaging/sync_from_upstream.py
python3 plugin-packaging/sync_from_upstream.py --check
python3 plugin-packaging/validate.py
```

同步器会校验当前 canonical skills/tools 与 `main` 完全一致；如果上游修改了两处便携性
补丁的上下文，它会失败并要求人工复核，而不会静默套用可能错误的替换。

## 发布到 fork

检查 `git diff` 后，将 `codex-plugin` 分支提交并推送到：

```bash
git push -u origin codex-plugin
```

提交和推送是远端写操作；让 Codex 代办时应分别明确授权。

## 从 GitHub 安装到本地 Codex 环境

> [!NOTE]
> 下述 Git marketplace/CLI 流程只安装到本机 Codex 环境，不会把插件发布到
> ChatGPT 网页版。网页版插件仅在 ChatGPT Work 的 **Plugins** 页面可用；若要在
> 网页端分发本插件，需要通过个人/工作区共享或
> [OpenAI 插件提交流程](https://developers.openai.com/plugins/deploy/submission)发布。
> 参见 [ChatGPT 插件说明](https://learn.chatgpt.com/docs/plugins)。

远端 `codex-plugin` 分支存在后，添加 Git marketplace：

```bash
codex plugin marketplace add ruuus/ai-berkshire-plugin \
  --ref codex-plugin \
  --sparse .agents/plugins \
  --sparse plugins/ai-berkshire
```

确认 marketplace 中能看到插件，然后安装：

```bash
codex plugin list --marketplace ai-berkshire-plugin --available --json
codex plugin add ai-berkshire@ai-berkshire-plugin
```

重启 Codex CLI 或 ChatGPT 桌面客户端中的 Codex 环境并新建线程，测试：

```text
使用 ai-berkshire:investment-team 研究一家上市公司
```

插件只有雪球抓取工具需要额外依赖：

```bash
python -m pip install -r <插件安装目录>/requirements-optional.txt
python -m playwright install chromium
```

## 获取后续更新

先刷新 Git marketplace 快照，再重新安装插件：

```bash
codex plugin marketplace upgrade ai-berkshire-plugin
codex plugin add ai-berkshire@ai-berkshire-plugin
```

随后新建线程，避免旧线程继续使用更新前已加载的 skill 内容。

## 本地检查

```bash
python3 plugins/ai-berkshire/tools/plugin_doctor.py
```

`WARN playwright` 只表示雪球工具的可选依赖未安装；核心估值、数据和报告审计工具仍可用。

本项目仅供学习和研究，不构成投资建议。插件分发须保留 `LICENSE` 和 `NOTICE`。
