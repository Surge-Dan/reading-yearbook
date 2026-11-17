# 检查与复现

当前浏览器验收基线是Windows桌面与Edge，不宣称所有宿主均已验证。所有默认测试使用合成数据，不读取账号、不调用微信读书或模型。

## 依赖

使用Python3.9+、Node22.20+及Edge。开发环境执行：

```powershell
python -m pip install -r requirements-dev.txt
npm install --ignore-scripts --no-audit --no-fund
```

Python版与Node版Playwright是两项不同依赖。完整检查会预检，缺失时明确失败；运行时不自行安装软件。已有运行时可设置NODE_PATH、SHARE_NODE、SHARE_PLAYWRIGHT；有环境覆盖支持的浏览器脚本使用BROWSER_EXECUTABLE／SHARE_BROWSER。部分历史UI测试仍以标准Windows Edge路径为基线。

## 两个入口

```powershell
# 核心回归，不代表浏览器全部验收
python -X utf8 tests/run_checks.py --quick

# 完整已配置检查：Python回归＋Node浏览器导出
python -X utf8 tests/run_checks.py
```

完整入口覆盖三种分享比例、选择与撤销、当前蒸馏阅读页、Markdown和PDF封面准备／实际PDF文件。GitHub Actions在Windows上执行同一入口。发布前另运行skill_release校验清单和新安装的0／1／15本合成场景。

## 必须保留的用例

- 零书目、无笔记、只有笔记、部分同步、未知进度、坏封面、长标题和较多书目。
- 日历闰年、54周年份、时区、跨年键、真实零、缺记录和未来；不能退回月度折线来掩盖数据缺失。
- 刷新、数据增删、原句变更、清空、撤销、存储损坏／禁用／空间不足；恢复后实际PNG／ZIP可导出。
- 私密材料过滤、恶意文本、错误结果包及真实／sample混用。
- 390／768／1440宽度、三种图片比例、字体回退和文字碰撞；预览与下载一致。
- 离线且无本机Noto字体、字体加载接口拒绝时仍能下载PNG；脚本中的伪HTML结束标签与Unicode分隔符不会破坏装配。
- Windows CRLF与LF文本指纹等价，实际内容篡改仍失败；同一依赖环境下，源码与新安装输出字节一致。不同fontTools版本的压缩字节不作为跨版本一致性承诺。

示例源码或画布变化后，用examples/build_html_demo.py及examples/export_html_demo.cjs重建公开示例，再刷新发行清单。校验失败不能只改断言掩盖问题；已移除功能应更新旧验收标准。

## 结果边界

快速模式会列出排除的Python UI模块；不能把它称为完整验收。浏览器依赖不可用、跳过的用例、实时接口、真实长书语义质量以及其他操作系统的缺口分别说明。记录以对应提交和实际日志为准，不照搬旧版测试数量。
