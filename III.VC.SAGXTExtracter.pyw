import os
import errno
import gta.gxt
from PyQt5 import QtWidgets, QtGui, Qt
from PyQt5.QtWidgets import QFileDialog, QTextBrowser, QMessageBox
from PyQt5.QtCore import QUrl
import sys

class GXTViewer(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("GXT文本查看器 By：Lzh10_慕黑")
        self.resize(800, 600)  # Set the initial window size to 800x600

        font = QtGui.QFont("Microsoft YaHei UI", 9)
        app = QtWidgets.QApplication.instance()
        app.setFont(font)

        layout = QtWidgets.QVBoxLayout()

        self.gxt_path_label = QtWidgets.QLabel("GXT 路径:")
        layout.addWidget(self.gxt_path_label)

        self.gxt_path_entry = QtWidgets.QLineEdit(self)
        layout.addWidget(self.gxt_path_entry)

        self.select_button = QtWidgets.QPushButton("选择 GXT 文件", self)
        self.select_button.clicked.connect(self.select_gxt_file)
        layout.addWidget(self.select_button)

        self.open_button = QtWidgets.QPushButton("打开", self)
        self.open_button.clicked.connect(self.open_gxt_from_input)
        layout.addWidget(self.open_button)

        self.about_button = QtWidgets.QPushButton("关于", self)
        self.about_button.clicked.connect(self.open_about_window)
        layout.addWidget(self.about_button)

        self.output_text = QTextBrowser(self)
        layout.addWidget(self.output_text)

        self.setLayout(layout)

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
                QMessageBox.critical(self, "错误", "找不到同名的txt文本文件")
        else:
            QMessageBox.critical(self, "错误", "无效的GXT文件路径")

    def select_gxt_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择GXT文件", "", "GXT文件 (*.gxt)")
        if file_path:
            self.gxt_path_entry.clear()
            self.gxt_path_entry.setText(file_path)
            self.open_gxt_path(file_path)

    def open_gxt_from_input(self):
        file_path = self.gxt_path_entry.text()
        self.open_gxt_path(file_path)

    def open_about_window(self):
        about_text = """
        版本号：Release Version 1.2.1<br/>
        更新日期：2023年11月4日<br/><br/>

        ☆☆☆☆★★★★★★☆☆☆☆<br/><br/>

        本软件由Lzh10_慕黑创作<br/>
        借用GitHub上开源GXT解析代码<br/>

        温馨提示：仅支持III、VC和SA版本GXT解析<br/><br/>

        此工具完全免费且开源，若通过付费渠道获取均为盗版！<br/>
        若您是盗版受害者，联系QQ：<a href="tencent://message/?uin=235810290&Site=&Menu=yes" 
        target="_blank" title="点击添加好友">235810290</a><br/><br/>

        免责声明：使用本软件导致的版权问题概不负责！<br/><br/>

        开源&检测更新：<a href="https://github.com/Lzh102938/III.VC.SAGXTExtracter">https://github.com/Lzh102938/III.VC.SAGXTExtracter<br/><br/></a>

        ☆☆☆☆★★★★★★☆☆☆☆<br/><br/>

        更新日志：<br/>
        V1.2.1 重构GUI，可自由改变窗口大小分辨率<br/>
        V1.2 修复了命令行输入导致输入路径错误问题，支援GTA3<br/>
        V1.1 添加了TABLE分文本功能<br/>
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

    if len(sys.argv) == 2 and sys.argv[1].endswith(".gxt"):
        gxt_path = sys.argv[1]
        window = GXTViewer()
        window.show()
        window.open_gxt_path(gxt_path)
    else:
        window = GXTViewer()
        window.show()

    app.exec_()

if __name__ == '__main__':
    main()
