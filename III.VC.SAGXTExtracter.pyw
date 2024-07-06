import os
import errno
import gta.gxt
import ctypes
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGroupBox, QFileDialog,
    QMessageBox, QTableWidget, QTableWidgetItem, QLineEdit, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import sys

myappid = "III.VC.SAGXTExtracter"
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

class ClickableLabel(QLabel):
    clicked = QtCore.pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()

class CustomTableWidgetItem(QTableWidgetItem):
    def __init__(self, text=""):
        super().__init__(text)

    def paint(self, painter, option, index):
        painter.save()
        painter.setPen(QtGui.QPen(Qt.black, 2))
        painter.drawText(option.rect, Qt.AlignLeft, self.text())
        painter.setPen(QtGui.QPen(Qt.white, 1))
        painter.drawText(option.rect, Qt.AlignLeft, self.text())
        painter.restore()

class GXTViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.gxt_file_path = None
        self.gxt_txt_path = None
        self.parsed_content = ""  # 新增属性
        self.initUI()

    def initUI(self):
        self.setWindowIcon(QIcon('./favicon.ico'))
        self.setWindowTitle("GXT文本查看器 - By：Lzh10_慕黑 | GTAmod中文组")
        self.resize(960, 618)

        font = QtGui.QFont("Microsoft YaHei UI", 10)
        app = QApplication.instance()
        app.setFont(font)

        main_layout = QVBoxLayout()

        control_layout = QVBoxLayout()

        self.gxt_path_entry = QLineEdit(self)
        control_layout.addWidget(self.gxt_path_entry)

        self.title_label = ClickableLabel("<h1>GXT文本查看器</h1>")
        self.title_label.setOpenExternalLinks(True)
        self.title_label.setToolTip("点击以显示「关于」")
        self.title_label.clicked.connect(self.open_about_window)
        control_layout.addWidget(self.title_label)

        button_groupbox = QGroupBox("操作")
        button_layout = QHBoxLayout()

        self.browse_button = QPushButton("📄 浏览GXT", self)
        self.browse_button.clicked.connect(self.select_gxt_file)
        self.browse_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 10px; padding: 5px; }") #边框粗细像素、圆角曲率、边框垂直距离
        self.browse_button.setToolTip("选择并解析GXT")
        button_layout.addWidget(self.browse_button)
        
        self.convert_button = QPushButton("🔄 码表转换", self)
        self.convert_button.clicked.connect(self.convert_using_table)
        self.convert_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 10px; padding: 5px; }")
        self.convert_button.setToolTip("将原密文二次解析")
        button_layout.addWidget(self.convert_button)

        self.save_button = QPushButton("💾 保存文本", self)
        self.save_button.clicked.connect(self.save_generated_txt)
        self.save_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 10px; padding: 5px; }")
        self.save_button.setToolTip("另存为 TXT")
        button_layout.addWidget(self.save_button)

        self.clear_button = QPushButton("🗑️ 清空表格", self)
        self.clear_button.clicked.connect(self.clear_table)
        self.clear_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 10px; padding: 5px; }")
        self.clear_button.setToolTip("清除历史表格内容")
        button_layout.addWidget(self.clear_button)

        button_groupbox.setLayout(button_layout)
        control_layout.addWidget(button_groupbox)

        main_layout.addLayout(control_layout)

        self.output_table = QTableWidget(self)
        self.output_table.setColumnCount(2)
        self.output_table.setHorizontalHeaderLabels(["键值", "内容"])
        self.output_table.horizontalHeader().setStretchLastSection(True)
        main_layout.addWidget(self.output_table)

        self.setLayout(main_layout)
        self.setAcceptDrops(True)

    def convert_using_table(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择转换表文件", "", "文本文件 (*.txt)")
        if file_path:
            try:
                gxt_file_path = self.gxt_file_path or self.gxt_path_entry.text()
                if not gxt_file_path:
                    gxt_file_path, _ = QFileDialog.getOpenFileName(self, "选择GXT文件", "", "GXT文件 (*.gxt)")
                    if not gxt_file_path:
                        raise FileNotFoundError("GXT文件路径未提供或选择")

                gxt_txt_path = os.path.splitext(gxt_file_path)[0] + '.txt'

                with open(gxt_txt_path, 'r', encoding='utf-8') as gxt_txt_file:
                    converted_lines = gxt_txt_file.readlines()

                with open(file_path, 'r', encoding='utf-8') as table_file:
                    hex_table = table_file.readlines()

                conversion_dict = {}
                for line in hex_table:
                    line = line.strip().split('\t')
                    if len(line) == 2:
                        conversion_dict[line[1]] = line[0]

                updated_lines = []
                for line in converted_lines:
                    if '=' in line:
                        key, value = line.split('=', 1)
                        converted_value = "".join(
                            conversion_dict.get(f"{ord(char):04x}", char) if ord(char) > 127 else char 
                            for char in value
                        )
                        updated_lines.append(f"{key}={converted_value}")
                    else:
                        updated_lines.append(line)

                with open(gxt_txt_path, 'w', encoding='utf-8') as output_file:
                    output_file.writelines(updated_lines)

                self.display_gxt_content_in_table('\n'.join(updated_lines))

                QMessageBox.information(self, "提示", f"文本转换完成并保存到 {gxt_txt_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"转换过程中出现错误: {str(e)}")
        else:
            QMessageBox.warning(self, "警告", "未选择转换表文件！")

    @staticmethod
    def createOutputDir(path: str):
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    @staticmethod
    def readOutTable(gxt, reader, name: str, outDirName: str):
        output_file_path = os.path.join(outDirName, name + '.txt')
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(f'[{name}]\n')
            for text in reader.parseTKeyTDat(gxt):
                f.write(text[0] + '=' + text[1] + '\n')

    def gxt_processing(self, file_path: str, outDirName: str):
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
                    self.gxt_txt_path = os.path.join(os.path.dirname(file_path), f"{gxt_name}.txt")
                    with open(self.gxt_txt_path, 'w', encoding='utf-8') as output_file:
                        for text in text_content:
                            output_file.write(f"{text[0]}={text[1]}\n")
                else:
                    gxt_dir = os.path.join(os.path.dirname(file_path), gxt_name)
                    self.createOutputDir(gxt_dir)
                    Tables = gxtReader.parseTables(gxt) if gxtReader.hasTables() else []

                    for table_name, _ in Tables:
                        self.readOutTable(gxt, gxtReader, table_name, gxt_dir)

                    text_content = []
                    for table_name, _ in Tables:
                        table_file_path = os.path.join(gxt_dir, table_name + '.txt')
                        with open(table_file_path, 'r', encoding='utf-8') as table_file:
                            text_content.append(table_file.read())

                    self.gxt_txt_path = os.path.join(os.path.dirname(file_path), f"{outDirName}.txt")
                    with open(self.gxt_txt_path, 'w', encoding='utf-8') as output_file:
                        output_file.write('\n\n'.join(text_content))

                return text_content
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开GXT文件时出错: {str(e)}")
            return []

    def display_gxt_content_in_table(self, content: str):
        self.parsed_content = content  # 将内容存储在属性中
        self.output_table.setRowCount(0)
        for line in content.splitlines():
            if line.startswith('[') and line.endswith(']'):
                row_position = self.output_table.rowCount()
                self.output_table.insertRow(row_position)
                self.output_table.setItem(row_position, 0, CustomTableWidgetItem(line.strip()))
                self.output_table.setItem(row_position, 1, CustomTableWidgetItem(""))
            elif '=' in line:
                key, value = line.split('=', 1)
                row_position = self.output_table.rowCount()
                self.output_table.insertRow(row_position)
                key_item = CustomTableWidgetItem(key.strip())
                key_item.setFlags(QtCore.Qt.ItemIsEnabled)
                value_item = CustomTableWidgetItem(value.strip())
                value_item.setFlags(QtCore.Qt.ItemIsEnabled)
                font = QtGui.QFont("Microsoft YaHei", 13, QtGui.QFont.Bold)
                value_item.setFont(font)
                self.output_table.setItem(row_position, 0, key_item)
                self.output_table.setItem(row_position, 1, value_item)

    def open_gxt_path(self, file_path: str):
        if os.path.isfile(file_path) and file_path.lower().endswith(".gxt"):
            self.gxt_file_path = file_path
            outDirName = os.path.splitext(os.path.basename(file_path))[0]
            text_content = self.gxt_processing(file_path, outDirName)
            self.output_table.clearContents()
            output_txt_path = os.path.join(os.path.dirname(file_path), f"{outDirName}.txt")
            if os.path.isfile(output_txt_path):
                with open(output_txt_path, 'r', encoding='utf-8') as output_file:
                    self.display_gxt_content_in_table(output_file.read())
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

    def save_generated_txt(self):
      if not self.parsed_content:
            QMessageBox.warning(self, "警告", "请先选择并解析GXT文件！")
            return

      txt_file_path = QFileDialog.getSaveFileName(self, "保存为TXT文件", os.path.splitext(self.gxt_txt_path)[0], "文本文件 (*.txt)")[0]
      if not txt_file_path:
           return

      try:
           with open(txt_file_path, 'w', encoding='utf-8') as target_file:
             target_file.write(self.parsed_content)
           QMessageBox.information(self, "提示", f"文件已保存到 {txt_file_path}")
      except Exception as e:
          QMessageBox.critical(self, "错误", f"保存文件时出错: {str(e)}")

    def clear_table(self):
        self.output_table.clearContents()
        self.output_table.setRowCount(0)

    def open_about_window(self):
        about_text = """
        版本号：Release Version 1.2.5<br/>
        更新日期：2024年7月6日<br/><br/>

        ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––<br/><br/>

        本软件由「Lzh10_慕黑」创作，隶属「GTAmod中文组」<br/>
        借用GitHub上开源GXT解析代码<br/>

        温馨提示：仅支持III、VC、SA、IV版本GXT解析<br/><br/>

        此工具完全免费且开源，若通过付费渠道获取均为盗版！<br/>
        若您是盗版受害者，联系QQ：<a href="tencent://message/?uin=235810290&Site=&Menu=yes"target="_blank" title="点击添加好友">235810290</a><br/><br/>

        免责声明：使用本软件导致的版权问题概不负责！<br/><br/>

        开源&检测更新：<a href="https://github.com/Lzh102938/III.VC.SAGXTExtracter">https://github.com/Lzh102938/III.VC.SAGXTExtracter<br/><br/></a>

        ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––<br/><br/>

        更新日志：<br/>        
        ☆☆☆☆☆☆☆★★★★★★★★★★★☆☆☆☆☆☆☆<br/>
        V1.2.5 优化GUI，为按钮显示注释；并添加另存为文本和清除表格功能</br>
        V1.2.4A 添加针对GTAIV的GXT解析<br/>
        V1.2.4 添加针对GTAIV的GXT解析（不包括中文）<br/>
        V1.2.3 优化GUI，按钮变为圆角设计，添加文件拖入窗口输入操作<br/>
        V1.2.2 添加功能，实现提取文本进行码表转换功能<br/>
        V1.2.1 重构GUI，可自由改变窗口大小分辨率<br/>
        V1.2   修复了命令行输入导致输入路径错误问题，支援GTA3<br/>
        V1.1   添加了TABLE分文本功能<br/>
        ☆☆☆☆☆☆☆★★★★★★★★★★★☆☆☆☆☆☆☆<br/>
        """
        about_dialog = QMessageBox(self)
        about_dialog.setWindowTitle("关于")
        about_dialog.setText(about_text)
        about_dialog.setIcon(QMessageBox.Information)
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
    app = QApplication([])

    window = GXTViewer()
    window.show()

    if len(sys.argv) == 2 and sys.argv[1].endswith(".gxt"):
        gxt_path = sys.argv[1]
        window.gxt_file_path = gxt_path
        window.open_gxt_path(gxt_path)

    app.exec_()

if __name__ == '__main__':
    main()
