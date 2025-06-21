[![image.png](https://i.postimg.cc/qBGjGZtn/image.png)](https://postimg.cc/F17yrpVs)

# 几乎可用于全版本GTA的GXT查看器

已经支持 GTA3、GTAVC、GTASA、GTA4 的 GXT 解析！

> **亦可使用网页端 👉 [https://gxtviewer.pages.dev/](https://gxtviewer.pages.dev/)**

---

> 本工具以 Silent 的源代码为基础，加入了可视化界面以及添加了其他 GTA 版本的支持。  
> 原开源链接 👉 [https://github.com/CookiePLMonster/GXT-Extractor](https://github.com/CookiePLMonster/GXT-Extractor)

> 对于 GTA3 版本的 GXT 文件，由于没有表，故程序不会输出 GTA3 的分文本，仅输出集成文本。  
> GTAVC、SA、IV 版本的 GXT 皆会输出集成文本和分文本。  

> 工具内集成了 **码表转换功能**，方便解析 GXT 时遇到二次转换的需求。  

---

## 较于其他工具

- ✅ **支持 Unicode**
- ✅ **拥有可视化界面**
- ✅ **支持版本更全面**
- ✅ **可使用码表转换**
- ✅ **符合生成的格式**
- ✅ **GUI 拖动输入和命令行输入**
- ✅ **自动更新，常用常新**

---

## 安装

**运行 Python 源代码或者安装应用程序**

- 源代码 👉 [https://github.com/Lzh102938/III.VC.SAGXTExtracter](https://github.com/Lzh102938/III.VC.SAGXTExtracter)
- 应用程序 👉 [https://github.com/Lzh102938/III.VC.SAGXTExtracter/releases/latest](https://github.com/Lzh102938/III.VC.SAGXTExtracter/releases/latest)

---

## 关于

| 类别   | 信息                   |
| ------ | ---------------------- |
| 版本号 | Release Version 2.1.0  |
| 更新日期 | 2025年4月20日        |

> **本软件由「Lzh10_慕黑」创作，隶属「GTAmod中文组」**  
> 借用 GitHub 上开源 GXT 解析代码

---

## 温馨提示

仅支持 III、VC、SA、IV 版本 GXT 解析

---

此工具完全免费且开源，若通过付费渠道获取均为盗版！  
若您是盗版受害者，联系 QQ：235810290

> **免责声明：使用本软件导致的版权问题本组概不负责！**

---

开源 & 检测更新 👉 [https://github.com/Lzh102938/III.VC.SAGXTExtracter](https://github.com/Lzh102938/III.VC.SAGXTExtracter)

---

## 更新日志

> **注意：由于添加了一些功能，处理文本时窗口可能未响应，请耐心等待。**

### V2.1.0

- 优化 GUI，使用蓝白主题样式
- 使用 GUI 基础框架包，设计风格统一
- 优化表格性能，减少滚动时卡顿
- 统一表格字号，统一行高，减轻渲染负担
- 专门设计滚动条，采用平面圆角滚动条
- 优化增减行处理逻辑，更安全处理行
- 增减行按钮设定绿红色，+ 按钮会变绿色，- 按钮会变红色
- 增加按钮变色，焦点悬浮至按钮时，按钮颜色将变深
- 新增检查更新功能，时刻保持最新

### V2.0.0

- 添加编辑功能，可在文本框内直接编辑文本并且「保存为GXT」
- 添加分表查找功能，可通过下拉栏定位所选表的「段落」
- 添加检索功能，可键入文本以检索对应内容
- 编辑功能可自由增减行数
- 仅保留简体中文语言，用户可自行添加语言
- 加横向滚动条，防止文本显示不完全
- 关于窗口添加滚动条，防止文本超出屏幕限制
- 优化表格性能，取消粗体显示

### 以下是 1.0 版本的更新日志

- **V1.2.6** 修正解析逻辑，修复遇到 UTF-16-LE 时无法解码字节的错误  
  修正说明页显示错误，换行错误与下一行相连  
  简化了冗杂代码，提取共通逻辑到辅助函数中  
  说明页重写，更新日志更美观  
- **V1.2.5** 优化 GUI，为按钮显示注释；并添加另存为文本和清除表格功能
- **V1.2.4A** 添加针对 GTAIV 的 GXT 解析
- **V1.2.4** 添加针对 GTAIV 的 GXT 解析（不包括中文）
- **V1.2.3** 优化 GUI，按钮变为圆角设计，添加文件拖入窗口输入操作
- **V1.2.2** 添加功能，实现提取文本进行码表转换功能
- **V1.2.1** 重构 GUI，可自由改变窗口大小分辨率
- **V1.2** 修复了命令行输入导致输入路径错误问题，支援 GTA3
- **V1.1** 添加了 TABLE 分文本功能

---

## 兼容性

Windows 10 以下的系统可能无法正常运行，建议进入 Github 下载源代码运行！

---

> 作者: Lzh10_慕黑  
> 原文章链接: [https://lzh102938.pages.dev/2024/07/07/支持GTA3，GTAVC，GTASA，GTAIV的字幕GXT工具/](https://lzh102938.pages.dev/2024/07/07/%E6%94%AF%E6%8C%81GTA3%EF%BC%8CGTAVC%EF%BC%8CGTASA%EF%BC%8CGTAIV%E7%9A%84%E5%AD%97%E5%B9%95GXT%E5%B7%A5%E5%85%B7/)
