# 发票小助手 v3.1 — 交付说明

## 本次完成内容（v3.1 增量）

1. **中文命名**：软件中文名为「发票小助手」，窗口标题同步更新。
2. **图标与角标**：`logo.png` 已转换为 `logo.ico`，作为 EXE 文件图标与运行后窗口左上角角标。
3. **体积压缩**：两层优化——①自定义 PyInstaller spec 剔除未使用的 OpenCV FFmpeg 视频插件、PIL AVIF 插件等冗余二进制；②用 UPX 4.2.4 压缩打包内嵌 DLL/pyd。EXE 体积从 v3.0 的 **123,418,777 字节（约 117.7 MB）** 降至 **84,810,070 字节（约 80.9 MB）**，整体下降约 **31%**。
4. **版本管理**：以新版本 `dist/发票小助手-v3.1.exe` 发布，旧版 `dist/InvoiceSorter.exe` 完整保留，不覆盖，并生成 `TEST_REPORT.md` 验收测试报告。
5. **一键打包脚本**：`build.bat` 改为使用自定义 spec，自动保留历史 EXE，并在检测到 UPX 时自动进一步压缩。
6. **文档更新**：`README.md`、`使用说明.txt`、`build.bat` 同步到 v3.1。

## 已继承的 v3.0 核心能力

- 多格式支持：PDF、JPG、JPEG、PNG、BMP、TIFF、WEBP
- 智能 OCR：图片与扫描件 PDF 自动识别
- 智能分类：13 大类（交通/餐饮/住宿/办公/通讯/物流/服务/医疗/水电/差旅/教育培训/图书/广告宣传）
- 统一命名：`2026年8月-交通类-820.00元.pdf`
- 四种归类方式：按月份+类型 / 按月份 / 按类型 / 覆盖源文件
- 处理报告：明细 + 分类金额统计
- 全英文版权：`Copyright (c) 2026 yingxiang.he@zkh.com. All rights reserved.`

## 关键决策

- **体积优化路径**：在不裁剪 OCR / PDF / GUI 核心能力的前提下，优先剔除可选二进制（视频编解码器、AVIF 插件），再用 UPX 压缩内嵌二进制。直接对最终 onefile EXE 跑 UPX 因 Windows `GUARD_CF` 限制无效，故改为 PyInstaller 打包阶段 `--upx-dir` 压缩内部 DLL/pyd，效果显著（-19%）。
- **图标实现**：`logo.ico` 多尺寸（16/24/32/48/64/128/256）嵌入 EXE；运行时通过 `sys._MEIPASS` 读取 `logo.ico` 设置窗口图标，同时保留 `logo.png` 作为高清图标照片。
- **版本发布策略**：不直接升级替换 `InvoiceSorter.exe`，而是生成新的 `发票小助手-v3.1.exe`，避免历史版本丢失。

## 文件清单

| 文件 | 说明 |
|------|------|
| `dist/发票小助手-v3.1.exe` | 新版单文件可执行程序（约 80.9 MB，UPX 压缩，已通过 OCR 自检与 GUI 拉起测试） |
| `dist/InvoiceSorter.exe` | 旧版单文件可执行程序（v3.0，已保留） |
| `发票小助手-v3.1.spec` | 自定义 PyInstaller spec（图标 + 体积优化） |
| `invoice_processor.py` | 主程序源码（v3.1） |
| `logo.ico` / `logo.png` | 软件图标 |
| `requirements.txt` | 依赖清单 |
| `build.bat` | 一键打包脚本（保留历史版本） |
| `README.md` / `使用说明.txt` | 项目文档 |
| `启动.bat` / `启动程序.bat` / `检查环境.bat` | 辅助脚本 |

## 注意事项

- 图片清晰度直接影响 OCR 识别率，建议使用原始清晰发票
- 覆盖源文件模式不可撤销，请先备份
- 首次处理会加载 OCR 引擎，稍慢属正常
- 若需重新打包，直接运行 `build.bat`（项目目录已内置 `upx.exe`，脚本会自动检测并复用）
