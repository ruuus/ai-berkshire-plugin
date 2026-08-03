# AI Berkshire Codex Plugin v{{VERSION}} 离线安装包

这个目录本身就是一个本地 Codex marketplace。安装期间请保留完整目录结构，尤其不要删除
`.agents/plugins/marketplace.json` 或 `plugins/ai-berkshire/`。

## 安装

1. 安装并登录最新版 Codex CLI。
2. 在 GitHub Release 页面下载 ZIP 或 tar.gz 以及 `SHA256SUMS`。
3. 校验下载文件的 SHA-256，并解压归档。
4. 把下面的占位路径替换为实际解压目录：

```bash
codex plugin marketplace add /absolute/path/to/ai-berkshire-plugin-v{{VERSION}}
codex plugin add ai-berkshire@ai-berkshire-plugin
```

安装后重启 Codex 或新建线程，并在 `/plugins` 中确认 **AI Berkshire** 已启用。

Codex CLI 不能直接安装 ZIP 或 tar.gz；必须先解压。只要该 marketplace 仍在配置中，
请保留解压目录。

## 升级

先下载并解压新版离线包到新目录，然后执行：

```bash
codex plugin remove ai-berkshire@ai-berkshire-plugin
codex plugin marketplace remove ai-berkshire-plugin
codex plugin marketplace add /absolute/path/to/new/ai-berkshire-plugin-vX.Y.Z
codex plugin add ai-berkshire@ai-berkshire-plugin
```

升级后请新建线程。确认新版可用后，可以删除旧版解压目录。

## 卸载

```bash
codex plugin remove ai-berkshire@ai-berkshire-plugin
codex plugin marketplace remove ai-berkshire-plugin
```

第一条命令删除已安装插件及本地缓存；第二条命令删除 marketplace 配置。完成后可以删除
离线包解压目录。

## 可选依赖

核心技能无需额外 Python 包。只有雪球抓取工具需要：

```bash
python -m pip install -r plugins/ai-berkshire/requirements-optional.txt
python -m playwright install chromium
```

本项目仅供学习和研究，不构成投资建议。插件分发须保留 `LICENSE` 和 `NOTICE`。
