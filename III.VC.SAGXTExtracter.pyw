import os
import errno
import gta.gxt
import ctypes
from PyQt5 import QtWidgets, QtGui, Qt, QtCore
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QGroupBox, QFileDialog, QMessageBox, QTextBrowser, QMainWindow
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QIcon
import sys

myappid = "III.VC.SAGXTExtracter"
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

class ClickableLabel(QLabel):
    clicked = QtCore.pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()

class GXTViewer(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowIcon(QIcon('./favicon.ico'))
        self.setWindowTitle("GXT文本查看器 - By：Lzh10_慕黑")
        self.resize(960, 618)  # Set the initial window size to 800x600

        font = QtGui.QFont("Microsoft YaHei UI", 10)
        app = QtWidgets.QApplication.instance()
        app.setFont(font)

        layout = QtWidgets.QVBoxLayout()
        
        self.gxt_path_entry = QtWidgets.QLineEdit(self)

        # 设置布局
        layout = QtWidgets.QVBoxLayout()

        # 添加文本框
        layout.addWidget(self.gxt_path_entry)
        
        # Title label (Clickable for About)
        self.title_label = ClickableLabel("<h1>GXT文本查看器</h1>")
        self.title_label.setOpenExternalLinks(True)
        self.title_label.setToolTip("点击以显示「关于」")
        self.title_label.clicked.connect(self.open_about_window)  # 连接到打开关于窗口的槽函数
        layout.addWidget(self.title_label)

        # Create group box for buttons
        button_groupbox = QGroupBox("操作")
        button_layout = QVBoxLayout()

        # Browse GXT Button
        self.browse_button = QPushButton("📄 浏览GXT", self)
        self.browse_button.clicked.connect(self.select_gxt_file)
        self.browse_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 10px; padding: 5px; }")
        button_layout.addWidget(self.browse_button)
        
        # Convert Button
        self.convert_button = QPushButton("🔄 码表转换", self)
        self.convert_button.clicked.connect(self.convert_using_table)
        self.convert_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 10px; padding: 5px; }")
        button_layout.addWidget(self.convert_button)

        button_groupbox.setLayout(button_layout)
        layout.addWidget(button_groupbox)

        # Output Text Browser
        self.output_text = QTextBrowser(self)
        self.output_text.setFont(QtGui.QFont("Microsoft YaHei UI", 12))
        layout.addWidget(self.output_text)

        # Set layout
        self.setLayout(layout)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
    def convert_using_table(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择转换表文件", "", "文本文件 (*.txt)")
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as table_file:
                hex_table = table_file.readlines()  # 读取转换表

            # 将非ASCII字符转换为对应的字符
            converted_text = ""
            input_text = self.output_text.toPlainText()  # 获取当前文本框中的文本
            for char in input_text:
                if ord(char) > 127:  # 非ASCII字符
                    hex_value = f"{ord(char):04x}"
                    for line in hex_table:
                        line = line.strip().split('\t')
                        if len(line) == 2 and line[1] == hex_value:
                            converted_text += line[0]
                            break
                    else:
                        converted_text += char
                else:
                    converted_text += char
                    
            self.output_text.setPlainText(converted_text)

            # 保存转换后的文本到txt文件中
            output_txt_path = os.path.join(os.path.dirname(file_path), "converted_text.txt")
            with open(output_txt_path, 'w', encoding='utf-8') as output_file:
                output_file.write(converted_text)

            QMessageBox.information(self, "提示", "文本转换完成并保存到converted_text.txt")

    def createOutputDir(self, path):
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def readOutTable(self, gxt, reader, name, outDirName):
        output_file_path = os.path.join(outDirName, name + '.txt')

        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(f'[{name}]\n')

            for text in reader.parseTKeyTDat(gxt):
                f.write(text[0] + '=' + text[1] + '\n')

    def gxt_processing(self, file_path, outDirName):
        gxt_name = os.path.splitext(os.path.basename(file_path))[0]

        try:
            with open(file_path, 'rb') as gxt:
                gxtversion = gta.gxt.getVersion(gxt)

                if not gxtversion:
                    QMessageBox.critical(self, "错误", "未知GXT版本！")
                    return []

                QMessageBox.information(self, "提示", f"成功识别GXT版本：{gxtversion}")

                gxtReader = gta.gxt.getReader(gxtversion)

                if gxtversion == 'iii':
                    text_content = gxtReader.parseTKeyTDat(gxt)
                    output_txt_path = os.path.join(os.path.dirname(file_path), f"{gxt_name}.txt")
                    with open(output_txt_path, 'w', encoding='utf-8') as output_file:
                        for text in text_content:
                            output_file.write(f"{text[0]}={text[1]}\n")
                else:
                    gxt_dir = os.path.join(os.path.dirname(file_path), gxt_name)
                    self.createOutputDir(gxt_dir)

                    Tables = []
                    if gxtReader.hasTables():
                        Tables = gxtReader.parseTables(gxt)

                    for t in Tables:
                        table_name = t[0]
                        self.readOutTable(gxt, gxtReader, table_name, gxt_dir)

                    text_content = []
                    for t in Tables:
                        table_name = t[0]
                        table_file_path = os.path.join(gxt_dir, table_name + '.txt')
                        with open(table_file_path, 'r', encoding='utf-8') as table_file:
                            text_content.append(table_file.read())

                    output_txt_path = os.path.join(os.path.dirname(file_path), outDirName + '.txt')
                    with open(output_txt_path, 'w', encoding='utf-8') as output_file:
                        output_file.write('\n\n'.join(text_content))

                return text_content
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开GXT文件时出错: {str(e)}")
            return []

    def open_gxt_path(self, file_path):
        if os.path.isfile(file_path) and file_path.lower().endswith(".gxt"):
            outDirName = os.path.splitext(os.path.basename(file_path))[0]
            text_content = self.gxt_processing(file_path, outDirName)
            self.output_text.clear()

            output_txt_path = os.path.join(os.path.dirname(file_path), outDirName + '.txt')
            if os.path.isfile(output_txt_path):
                with open(output_txt_path, 'r', encoding='utf-8') as output_file:
                    self.output_text.setPlainText(output_file.read())
            else:
                QMessageBox.critical(self, "错误", "找不到同名的txt文本文件！")
        else:
            QMessageBox.critical(self, "错误", "无效的GXT文件路径！")

    def select_gxt_file(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(self, "选择GXT文件", "", "GXT文件 (*.gxt)")
            if file_path:
                self.gxt_path_entry.clear()
                self.gxt_path_entry.setText(file_path)
                self.open_gxt_path(file_path)
        except Exception as e:
            print("Error:", e)
        
    def open_gxt_from_input(self):
        file_path = self.gxt_path_entry.text()
        self.open_gxt_path(file_path)

    def open_about_window(self):
        about_text = """
        版本号：Release Version 1.2.3<br/>
        更新日期：2024年3月30日<br/><br/>

        ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––<br/><br/>

        本软件由「Lzh10_慕黑」创作<br/>
        借用GitHub上开源GXT解析代码<br/>

        温馨提示：仅支持III、VC和SA版本GXT解析<br/><br/>

        此工具完全免费且开源，若通过付费渠道获取均为盗版！<br/>
        若您是盗版受害者，联系QQ：<a href="tencent://message/?uin=235810290&Site=&Menu=yes" 
        target="_blank" title="点击添加好友">235810290</a><br/><br/>

        免责声明：使用本软件导致的版权问题概不负责！<br/><br/>

        开源&检测更新：<a href="https://github.com/Lzh102938/III.VC.SAGXTExtracter">https://github.com/Lzh102938/III.VC.SAGXTExtracter<br/><br/></a>

        ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––<br/><br/>

        更新日志：<br/>        
        ☆☆☆☆☆☆☆★★★★★★★★★★★☆☆☆☆☆☆☆<br/>
        V1.2.3 优化GUI，按钮变为圆角设计，添加文件拖入窗口输入操作<br/>
        V1.2.2 添加功能，实现提取文本进行码表转换功能<br/>
        V1.2.1 重构GUI，可自由改变窗口大小分辨率<br/>
        V1.2   修复了命令行输入导致输入路径错误问题，支援GTA3<br/>
        V1.1   添加了TABLE分文本功能<br/>
        ☆☆☆☆☆☆☆★★★★★★★★★★★☆☆☆☆☆☆☆<br/>
        """

        about_dialog = QtWidgets.QMessageBox(self)
        about_dialog.setWindowTitle("关于")
        about_dialog.setText(about_text)
        about_dialog.setIcon(QtWidgets.QMessageBox.Information)
        about_dialog.exec_()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and len(event.mimeData().urls()) == 1:
            url = event.mimeData().urls()[0]
            if url.isLocalFile() and url.toLocalFile().lower().endswith(".gxt"):
                event.acceptProposedAction()

    def dropEvent(self, event):
        url = event.mimeData().urls()[0]
        gxt_path = url.toLocalFile()
        self.open_gxt_path(gxt_path)

def main():
    app = QtWidgets.QApplication([])

    window = GXTViewer()
    window.show()

    if len(sys.argv) == 2 and sys.argv[1].endswith(".gxt"):
        gxt_path = sys.argv[1]
        window.open_gxt_path(gxt_path)

    app.exec_()

if __name__ == '__main__':
    main()
