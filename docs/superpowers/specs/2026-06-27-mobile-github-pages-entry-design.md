# GitHub Pages 手机入口同步设计

## 背景

GitHub Pages 上的 `desktop_words.html` 已包含更新后的 `words_data.json` 内嵌词库，但页面静态 HTML 中仍残留旧的初始卡片内容，例如 `Please come here now.`。手机端或 PWA 在缓存和初始渲染影响下，可能继续看到旧内容。

## 目标

提供一个更稳定的手机访问入口：`https://distorzing.github.io/ogden-850/`。该入口应优先适配手机，并从 `words_data.json` 加载最新词库，避免旧的内嵌 HTML 和缓存造成误导。

## 方案

1. 新增 `index.html` 作为手机优先入口。
2. `index.html` 使用 `fetch('words_data.json?v=<版本>')` 和 `fetch('plan_data.json?v=<版本>')` 加载最新数据。
3. 页面展示今日新词，包含单词、音标、中文释义、英文例句、中文例句翻译。
4. 保留简单卡片/列表切换和本地完成状态。
5. 修复 `desktop_words.html` 中旧的硬编码初始卡片，改为加载提示，避免旧例句闪现。
6. 更新 `manifest.json` 的 `start_url` 为 `index.html`。
7. 更新 `sw.js` 缓存版本，并缓存 `index.html`、`words_data.json`、`plan_data.json`。

## 验证

- 本地打开 `index.html` 能看到最新例句和中文翻译。
- GitHub Pages 根链接可访问。
- 手机宽度无横向溢出。
- `desktop_words.html` 不再含旧初始例句 `Please come here now.`。
