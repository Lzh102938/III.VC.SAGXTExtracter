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

from master.about_window import open_about_window
from master.initUI import initUI
from master.convert_using_table import convert_using_table

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
        initUI(self)

    def convert_using_table(self):
        convert_using_table(self)

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

                if gxtversion == 'III':
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
        open_about_window(self)

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
