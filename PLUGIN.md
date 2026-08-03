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

## 安装、升级与卸载

> [!NOTE]
> 下述 marketplace/CLI 流程只安装到本机 Codex 环境，不会把插件发布到
> ChatGPT 网页版。网页版插件仅在 ChatGPT Work 的 **Plugins** 页面可用；若要在
> 网页端分发本插件，需要通过个人/工作区共享或
> [OpenAI 插件提交流程](https://developers.openai.com/plugins/deploy/submission)发布。
> 参见 [ChatGPT 插件说明](https://learn.chatgpt.com/docs/plugins)。

### 方式一：Git sparse 在线安装（推荐）

公开仓库无需 GitHub Token 或 SSH Key。添加 marketplace 时只拉取清单和插件目录：

```bash
codex plugin marketplace add ruuus/ai-berkshire-plugin \
  --ref codex-plugin \
  --sparse .agents/plugins \
  --sparse plugins/ai-berkshire
codex plugin add ai-berkshire@ai-berkshire-plugin
```

检查安装结果：

```bash
codex plugin marketplace list
codex plugin list
```

更新 Git sparse 安装：

```bash
codex plugin marketplace upgrade ai-berkshire-plugin
codex plugin add ai-berkshire@ai-berkshire-plugin
```

### 方式二：Release 离线安装

从 [GitHub Releases](https://github.com/ruuus/ai-berkshire-plugin/releases) 下载同一版本的
ZIP 或 tar.gz 以及 `SHA256SUMS`。先对照校验值，再解压归档；CLI 不能直接安装压缩包。

Linux/macOS 可计算：

```bash
sha256sum ai-berkshire-plugin-v0.2.0.zip
```

Windows PowerShell 可计算：

```powershell
Get-FileHash .\ai-berkshire-plugin-v0.2.0.zip -Algorithm SHA256
```

把占位路径替换为实际解压目录：

```bash
codex plugin marketplace add /absolute/path/to/ai-berkshire-plugin-v0.2.0
codex plugin add ai-berkshire@ai-berkshire-plugin
```

只要本地 marketplace 仍在配置中，请保留解压目录。离线包内置一份同样的
`README.md`，方便在断网环境中查看命令。

升级离线安装时，先下载并解压新版到新目录，再重新绑定本地 marketplace：

```bash
codex plugin remove ai-berkshire@ai-berkshire-plugin
codex plugin marketplace remove ai-berkshire-plugin
codex plugin marketplace add /absolute/path/to/new/ai-berkshire-plugin-vX.Y.Z
codex plugin add ai-berkshire@ai-berkshire-plugin
```

`marketplace upgrade` 只刷新 Git marketplace，因此不用于 Release 解压目录。

### 卸载

只删除插件、保留 marketplace 以便以后重新安装：

```bash
codex plugin remove ai-berkshire@ai-berkshire-plugin
```

同时移除该仓库的 marketplace 配置：

```bash
codex plugin marketplace remove ai-berkshire-plugin
```

离线安装用户完成上述两步后，可以删除对应的解压目录。

### 安装后验证

重启 Codex CLI 或 ChatGPT 桌面客户端中的 Codex 环境并新建线程，在 `/plugins` 中
确认插件已启用，然后测试：

```text
使用 ai-berkshire:investment-team 研究一家上市公司
```

插件只有雪球抓取工具需要额外依赖：

```bash
python -m pip install -r <插件安装目录>/requirements-optional.txt
python -m playwright install chromium
```

## 构建 Release 离线包

打包脚本会读取 manifest 版本，生成带顶层目录的 ZIP、tar.gz 和统一校验文件：

```bash
python3 plugin-packaging/build_release.py --output-dir dist --expected-version 0.2.0
```

输出文件：

```text
dist/ai-berkshire-plugin-v0.2.0.zip
dist/ai-berkshire-plugin-v0.2.0.tar.gz
dist/SHA256SUMS
```

推送与 manifest 版本一致的 `vX.Y.Z` 标签后，
`.github/workflows/plugin-release.yml` 会重新运行上游同步检查和插件校验，并自动创建
GitHub Release、上传以上三个文件。

## 本地检查

```bash
python3 plugins/ai-berkshire/tools/plugin_doctor.py
```

`WARN playwright` 只表示雪球工具的可选依赖未安装；核心估值、数据和报告审计工具仍可用。

本项目仅供学习和研究，不构成投资建议。插件分发须保留 `LICENSE` 和 `NOTICE`。
