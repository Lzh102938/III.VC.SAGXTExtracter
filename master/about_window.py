from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt

def open_about_window(parent):
    about_text = """
    <html>
    <body>
    <p>版本号：Release Version 1.2.6<br/>
    更新日期：2024年8月8日</p>

    <hr/>

    <p>本软件由「Lzh10_慕黑」创作，隶属「GTAmod中文组」<br/>
    借用GitHub上开源GXT解析代码</p>

    <p>温馨提示：仅支持III、VC、SA、IV版本GXT解析</p>

    <p>此工具完全免费且开源，若通过付费渠道获取均为盗版！<br/>
    若您是盗版受害者，联系QQ：<a href="tencent://message/?uin=235810290&Site=&Menu=yes" target="_blank" title="点击添加好友">235810290</a></p>

    <p>免责声明：使用本软件导致的版权问题概不负责！</p>

    <p>开源&检测更新：<a href="https://github.com/Lzh102938/III.VC.SAGXTExtracter">https://github.com/Lzh102938/III.VC.SAGXTExtracter</a></p>

    <hr/>

    <p>更新日志：<br/>        
    ☆☆☆☆☆☆☆★★★★★★★★★★★☆☆☆☆☆☆☆</p>
    <table>
        <tr>
            <td><b>V1.2.6</b></td>
            <td>
                <ul>
                    <li>修正解析逻辑，修复遇到UTF-16-LE时无法解码字节的错误</li>
                    <li>修正说明页显示错误，换行错误与下一行相连</li>
                    <li>简化了冗杂代码，提取共通逻辑到辅助函数中</li>
                    <li>说明页重写，更新日志更美观</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td><b>V1.2.5</b></td>
            <td>
                <ul>
                    <li>优化GUI，为按钮显示注释</li>
                    <li>添加另存为文本和清除表格功能</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td><b>V1.2.4A</b></td>
            <td>
                <ul>
                    <li>添加针对GTAIV的GXT解析</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td><b>V1.2.4</b></td>
            <td>
                <ul>
                    <li>添加针对GTAIV的GXT解析（不包括中文）</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td><b>V1.2.3</b></td>
            <td>
                <ul>
                    <li>优化GUI，按钮变为圆角设计，添加文件拖入窗口输入操作</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td><b>V1.2.2</b></td>
            <td>
                <ul>
                    <li>添加功能，实现提取文本进行码表转换功能</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td><b>V1.2.1</b></td>
            <td>
                <ul>
                    <li>重构GUI，可自由改变窗口大小分辨率</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td><b>V1.2</b></td>
            <td>
                <ul>
                    <li>修复了命令行输入导致输入路径错误问题，支援GTA3</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td><b>V1.1</b></td>
            <td>
                <ul>
                    <li>添加了TABLE分文本功能</li>
                </ul>
            </td>
        </tr>
    </table>
    <p>☆☆☆☆☆☆☆★★★★★★★★★★★☆☆☆☆☆☆☆</p>
    </body>
    </html>
    """
    about_dialog = QMessageBox(parent)
    about_dialog.setWindowTitle("关于")
    about_dialog.setTextFormat(Qt.RichText)
    about_dialog.setText(about_text)
    about_dialog.setIcon(QMessageBox.Information)
    about_dialog.exec_()
