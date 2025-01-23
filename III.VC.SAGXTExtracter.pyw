import os
import errno
import gta.gxt
import ctypes
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGroupBox, QFileDialog,
    QMessageBox, QTableWidget, QTableWidgetItem, QLineEdit, QWidget, QComboBox, QAbstractItemView, QDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QRegExpValidator, QFont
import sys
import shutil
import subprocess
import re

from master.about_window import open_about_window
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
        self.setFlags(self.flags() | Qt.ItemIsEditable)  # 设置为可编辑

class GXTViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.gxt_file_path = None
        self.gxt_txt_path = None
        self.parsed_content = ""
        self.translations = {}
        self.load_language_file()
        self.initUI()

    def load_language_file(self, lang_file_path='languages/简体中文.lang'):
        """Load translations from a language file, using \n as a newline delimiter for multiline content."""
        self.translations = {}
        with open(lang_file_path, 'r', encoding='utf-8') as lang_file:
            for line in lang_file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue  # Skip comments and empty lines

                if '=' in line:
                    key, value = line.split('=', 1)
                    self.translations[key.strip()] = value.strip()

        # Convert \n placeholders back to actual newlines in the content
        for key, value in self.translations.items():
            self.translations[key] = value.replace(r'\n', '\n')

    def load_available_languages(self):
        """Load available languages from the 'languages' directory."""
        self.available_languages = []
        for file in os.listdir('languages'):
            if file.endswith('.lang'):
                self.available_languages.append(file)

    def tr(self, key, **kwargs):
        """Helper function to retrieve translated text and format it."""
        return self.translations.get(key, key).format(**kwargs)

    def initUI(self):
        self.load_available_languages()

        self.setWindowIcon(QIcon('./favicon.ico'))
        self.setWindowTitle(self.tr("window_title"))
        self.resize(960, 618)

        font = QtGui.QFont("Microsoft YaHei UI", 10)
        app = QApplication.instance()
        app.setFont(font)

        main_layout = QVBoxLayout()

        control_layout = QVBoxLayout()

        self.language_selector = QComboBox(self)
        for lang in self.available_languages:
            self.language_selector.addItem(lang)
        self.language_selector.setCurrentText('简体中文.lang')
        self.language_selector.currentIndexChanged.connect(self.change_language)
        control_layout.addWidget(self.language_selector)

        self.gxt_path_entry = QLineEdit(self)
        self.gxt_path_entry.setVisible(False)  # Hides the QLineEdit without affecting its functionality
        control_layout.addWidget(self.gxt_path_entry)

        self.title_label = ClickableLabel("<h1>" + self.tr("window_title") + "</h1>")
        self.title_label.setOpenExternalLinks(True)
        self.title_label.setToolTip(self.tr("tooltip_browse_button"))
        self.title_label.clicked.connect(self.open_about_window)
        control_layout.addWidget(self.title_label)

        button_groupbox = QGroupBox("操作")
        button_layout = QHBoxLayout()

        self.browse_button = QPushButton(self.tr("browse_button_text"), self)
        self.browse_button.clicked.connect(self.select_gxt_file)
        self.browse_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 10px; padding: 5px; }")
        self.browse_button.setToolTip(self.tr("tooltip_browse_button"))
        button_layout.addWidget(self.browse_button)

        self.convert_button = QPushButton(self.tr("convert_button_text"), self)
        self.convert_button.clicked.connect(self.convert_using_table)
        self.convert_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 10px; padding: 5px; }")
        self.convert_button.setToolTip(self.tr("tooltip_convert_button"))
        button_layout.addWidget(self.convert_button)

        self.save_button = QPushButton(self.tr("save_button_text"), self)
        self.save_button.clicked.connect(self.save_generated_txt)
        self.save_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 10px; padding: 5px; }")
        self.save_button.setToolTip(self.tr("tooltip_save_button"))
        button_layout.addWidget(self.save_button)

        self.clear_button = QPushButton(self.tr("clear_button_text"), self)
        self.clear_button.clicked.connect(self.clear_table)
        self.clear_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 10px; padding: 5px; }")
        self.clear_button.setToolTip(self.tr("tooltip_clear_button"))
        button_layout.addWidget(self.clear_button)

        self.save_gxt_button = QPushButton(self.tr("save_gxt_button_text"), self)
        self.save_gxt_button.clicked.connect(self.save_and_build_gxt)
        self.save_gxt_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 10px; padding: 5px; }")
        self.save_gxt_button.setToolTip(self.tr("tooltip_save_gxt_button"))
        button_layout.addWidget(self.save_gxt_button)

        button_groupbox.setLayout(button_layout)
        control_layout.addWidget(button_groupbox)

        main_layout.addLayout(control_layout)

        self.section_combobox = QComboBox(self)
        self.section_combobox.currentTextChanged.connect(self.highlight_selected_section)
        main_layout.addWidget(self.section_combobox)

        self.output_table = QTableWidget(self)
        self.output_table.setColumnCount(3)  # 设置列数为3，增加操作列
        self.output_table.setHorizontalHeaderLabels([self.tr("table_column_key"), self.tr("table_column_value"), self.tr("change_the_row")])
        self.output_table.setEditTriggers(QAbstractItemView.DoubleClicked)  # 设置表格可编辑
        main_layout.addWidget(self.output_table)

        # 获取表格的头部
        header = self.output_table.horizontalHeader()

        # 设置列模式：第一列固定，第二列自适应，第三列固定
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)  # 第一列：固定宽度
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)  # 第二列：自适应
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)  # 第三列：固定宽度

        # 设置固定宽度
        self.output_table.setColumnWidth(0, 100)  # 第一列宽度固定，适合8个字符
        self.output_table.setColumnWidth(2, 80)  # 第三列宽度固定，适合按钮

        # 第二列宽度会随窗口大小变化
        self.search_entry = QLineEdit(self)
        self.search_entry.setPlaceholderText(self.tr("search_placeholder"))
        self.search_entry.textChanged.connect(self.filter_table)
        main_layout.addWidget(self.search_entry)

        self.setLayout(main_layout)
        self.setAcceptDrops(True)

    def change_language(self):
        selected_lang = self.language_selector.currentText()
        lang_file_path = os.path.join('languages', selected_lang)
        self.load_language_file(lang_file_path)
        self.update_ui_texts()

    def update_ui_texts(self):
        self.setWindowTitle(self.tr("window_title"))
        self.title_label.setText("<h1>" + self.tr("window_title") + "</h1>")
        self.browse_button.setText(self.tr("browse_button_text"))
        self.browse_button.setToolTip(self.tr("tooltip_browse_button"))
        self.convert_button.setText(self.tr("convert_button_text"))
        self.convert_button.setToolTip(self.tr("tooltip_convert_button"))
        self.save_button.setText(self.tr("save_button_text"))
        self.save_button.setToolTip(self.tr("tooltip_save_button"))
        self.clear_button.setText(self.tr("clear_button_text"))
        self.clear_button.setToolTip(self.tr("tooltip_clear_button"))
        self.save_gxt_button.setText(self.tr("save_gxt_button_text"))
        self.save_gxt_button.setToolTip(self.tr("tooltip_save_gxt_button"))
        self.output_table.setHorizontalHeaderLabels([self.tr("table_column_key"), self.tr("table_column_value"), "操作"])
        self.search_entry.setPlaceholderText(self.tr("search_placeholder"))

    def convert_using_table(self):
        convert_using_table(self)

    def readOutTable(self, gxt, reader, name: str, outDirName: str):
        output_file_path = os.path.join(outDirName, name + '.txt')
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(f'[{name}]\n')
            for text in reader.parseTKeyTDat(gxt):
                f.write(text[0] + '=' + text[1] + '\n')

    @staticmethod
    def createOutputDir(path: str):
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def gxt_processing(self, file_path: str, outDirName: str):
        gxt_name = os.path.splitext(os.path.basename(file_path))[0]
        try:
            with open(file_path, 'rb') as gxt:
                gxtversion = gta.gxt.getVersion(gxt)
                if not gxtversion:
                    QMessageBox.critical(self, self.tr("error"), self.tr("error_unknown_gxt_version"))
                    return []
                
                # 获取并设置窗口标题
                current_title = self.windowTitle()
                new_title = self.tr("title_version") + " " + gxtversion
                self.setWindowTitle(new_title)

                gxtReader = gta.gxt.getReader(gxtversion)

                # 处理 GTA III 版本
                if gxtversion == 'III':
                    text_content = gxtReader.parseTKeyTDat(gxt)
                    self.gxt_txt_path = os.path.join(os.path.dirname(file_path), f"{gxt_name}.txt")
                    with open(self.gxt_txt_path, 'w', encoding='utf-8') as output_file:
                        for text in text_content:
                            output_file.write(f"{text[0]}={text[1]}\n")
                
                else:
                    # 处理 VC 和 SA 版本
                    gxt_dir = os.path.join(os.path.dirname(file_path), gxt_name)
                    self.createOutputDir(gxt_dir)  # 确保文件夹存在

                    # 解析表格
                    Tables = gxtReader.parseTables(gxt) if gxtReader.hasTables() else []
                    
                    for table_name, _ in Tables:
                        self.readOutTable(gxt, gxtReader, table_name, gxt_dir)

                    # 汇总所有表格的内容
                    text_content = []
                    for table_name, _ in Tables:
                        table_file_path = os.path.join(gxt_dir, f"{table_name}.txt")
                        with open(table_file_path, 'r', encoding='utf-8') as table_file:
                            text_content.append(table_file.read())

                    # 将所有表格内容写入一个汇总文件
                    self.gxt_txt_path = os.path.join(os.path.dirname(file_path), f"{outDirName}.txt")
                    with open(self.gxt_txt_path, 'w', encoding='utf-8') as output_file:
                        output_file.write('\n\n'.join(text_content))

                return text_content
        
        except Exception as e:
            QMessageBox.critical(self, self.tr("error"), self.tr("error_opening_gxt_file", error=str(e)))
            return []
        
    def display_gxt_content_in_table(self, content: str):
        self.parsed_content = content
        self.output_table.blockSignals(True)  # 阻塞信号
        self.output_table.clearContents()  # 清空现有内容
        self.output_table.setRowCount(0)  # 重置行数

        lines = content.splitlines()
        section_names = []
        table_data = []
        row_section_map = {}  # 用于下拉栏定位段名
        row_index = 0

        # 直接在文本中查找[字符，并处理这些行
        for line in lines:
            if line.startswith('[') and line.endswith(']'):
                section_name = line[1:-1]
                section_names.append(section_name)
                row_section_map[section_name] = row_index
                table_data.append((line, "", row_index))
                row_index += 1
            elif '=' in line:
                key, value = line.split('=', 1)
                table_data.append((key.strip(), value.strip(), row_index))
                row_index += 1

        # 设置字体样式
        font_normal = QFont("Microsoft YaHei UI", 10)  # 字体：Microsoft YaHei UI，字号：10
        font_bold = QFont("Microsoft YaHei UI", 13)  # 字体：Microsoft YaHei UI，字号：10，粗体

        # 填充下拉栏
        self.section_combobox.clear()
        self.section_combobox.addItems(section_names)

        # 一次性设置行数和列数
        self.output_table.setRowCount(len(table_data))
        self.output_table.setColumnCount(3)

        # 批量更新表格内容
        table_items = []
        for key, value, row in table_data:
            key_item = QTableWidgetItem(key)
            value_item = QTableWidgetItem(value)
            table_items.append((row, key_item, value_item))
            
            # 设置字体样式
            if row == 0 or key_item.column() == 0:
                key_item.setFont(font_normal)
                value_item.setFont(font_normal)
            else:
                key_item.setFont(font_normal)
                value_item.setFont(font_bold)  # 设置第二列的字体加粗

        for row, key_item, value_item in table_items:
            self.output_table.setItem(row, 0, key_item)
            self.output_table.setItem(row, 1, value_item)
            self.add_row_buttons(row, key, section_names)

        self.output_table.blockSignals(False)  # 恢复信号
        self.output_table.update()  # 更新表格显示
        self.output_table.setUpdatesEnabled(True)  # 启用更新
        # 为下拉栏添加定位功能
        self.section_combobox.currentIndexChanged.connect(lambda idx: self.scroll_to_section(idx, row_section_map))

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
                QMessageBox.critical(self, self.tr("错误"), self.tr("error_invalid_gxt_file_path"))
        else:
            QMessageBox.critical(self, self.tr("错误"), self.tr("error_invalid_gxt_file_path"))

    def select_gxt_file(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(self, self.tr("select_gxt_file"), "", "GXT文件 (*.gxt)")
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
            QMessageBox.warning(self, self.tr("警告"), self.tr("warning_select_and_parse_gxt_first"))
            return

        txt_file_path = QFileDialog.getSaveFileName(self, self.tr("save_as_txt"), os.path.splitext(self.gxt_txt_path)[0], "文本文件 (*.txt)")[0]
        if not txt_file_path:
            return

        try:
            with open(txt_file_path, 'w', encoding='utf-8') as target_file:
                target_file.write(self.parsed_content)
            QMessageBox.information(self, self.tr("提示"), self.tr("info_file_saved", path=txt_file_path))
        except Exception as e:
            QMessageBox.critical(self, self.tr("错误"), self.tr("error_saving_file", error=str(e)))

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

    def save_and_build_gxt(self):
        if not self.gxt_file_path:
            QMessageBox.warning(self, self.tr("警告"), self.tr("warning_select_and_parse_gxt_first"))
            return

        # Set table to editable
        for row in range(self.output_table.rowCount()):
            item = self.output_table.item(row, 0)
            if item:
                item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)

        # Get the directory of the input .gxt file
        gxt_dir = os.path.dirname(self.gxt_file_path)
        debug_dir = os.path.join(gxt_dir, "Debug")

        # Clear the Debug directory
        if os.path.exists(debug_dir):
            shutil.rmtree(debug_dir)
        self.createOutputDir(debug_dir)

        # Determine the output text file name based on the version
        version = self.windowTitle().split()[-1]
        output_txt_path = {
            'III': os.path.join(debug_dir, "gta3.txt"),
            'VC': os.path.join(debug_dir, "gtavc.txt"),
            'SA': os.path.join(debug_dir, "gtasa.txt"),
            'IV': os.path.join(debug_dir, "gta4.txt")
        }.get(version)

        if not output_txt_path:
            QMessageBox.critical(self, self.tr("错误"), self.tr("error_unknown_gxt_version"))
            return

        # Save edited content to temporary file
        with open(output_txt_path, 'w', encoding='utf-8') as output_file:
            for row in range(self.output_table.rowCount()):
                key_item = self.output_table.item(row, 0)
                value_item = self.output_table.item(row, 1)
                if key_item and value_item:
                    line = f"{key_item.text()}={value_item.text()}\n"
                    if '[' in key_item.text():  # 判断键是否含有[
                        line = line.replace('=', '', 1)  # 删除第一个=号
                    output_file.write(line)

        # Copy builder exe to Debug directory
        builder_exe = {
            'III': 'LCGXTBuilder.exe',
            'VC': 'VCGXTBuilder.exe',
            'SA': 'SAGXTBuilder.exe',
            'IV': 'IVGXTBuilder.exe'
        }.get(version)

        if not builder_exe:
            QMessageBox.critical(self, self.tr("错误"), self.tr("error_unknown_gxt_version"))
            return

        builder_path = os.path.join("builder", builder_exe)
        debug_builder_path = os.path.join(debug_dir, builder_exe)

        if not os.path.isfile(builder_path):
            QMessageBox.critical(self, self.tr("错误"), self.tr("error_builder_exe_not_found", exe=builder_exe))
            return

        shutil.copy(builder_path, debug_builder_path)

        # Run builder exe
        try:
            subprocess.run([debug_builder_path, output_txt_path], check=True, cwd=debug_dir)
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, self.tr("错误"), self.tr("error_running_builder", error=str(e)))
            return

        # Search for any .gxt file in the Debug directory and copy to original directory
        gxt_files = [f for f in os.listdir(debug_dir) if f.endswith('.gxt')]
        if gxt_files:
            # Assuming there's only one .gxt file generated
            generated_gxt_path = os.path.join(debug_dir, gxt_files[0])
            edited_gxt_path = os.path.join(gxt_dir, f"{os.path.splitext(os.path.basename(self.gxt_file_path))[0]}_Edited.gxt")
            shutil.copy(generated_gxt_path, edited_gxt_path)
            QMessageBox.information(self, self.tr("提示"), self.tr("info_gxt_saved", path=edited_gxt_path))
        else:
            QMessageBox.critical(self, self.tr("错误"), self.tr("error_gxt_not_generated"))
        
    def add_row(self, row_position):
        """在指定行下方添加新行"""
        self.output_table.insertRow(row_position + 1)
        self.add_row_buttons(row_position + 1, "", self.section_combobox.currentText())
        # 重新设置所有按钮的点击事件
        for row in range(self.output_table.rowCount()):
            self.update_button_events(row)

    def update_button_events(self, row):
        """更新指定行的按钮点击事件"""
        button_widget = self.output_table.cellWidget(row, 2)
        if button_widget:
            add_button = button_widget.layout().itemAt(0).widget()
            delete_button = button_widget.layout().itemAt(1).widget()
            add_button.clicked.disconnect()
            delete_button.clicked.disconnect()
            add_button.clicked.connect(lambda: self.add_row(row))
            delete_button.clicked.connect(lambda: self.delete_row(row))

    def add_row_buttons(self, row_position, section_name, section_names):
        """为表格行添加操作按钮 (+ 和 -)。"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)
        button_layout.setContentsMargins(0, 0, 0, 0)

        add_button = QPushButton("+")
        add_button.setFixedSize(20, 20)
        add_button.clicked.connect(self.handle_add_button_clicked)
        button_layout.addWidget(add_button)

        delete_button = QPushButton("-")
        delete_button.setFixedSize(20, 20)
        delete_button.clicked.connect(self.handle_delete_button_clicked)
        button_layout.addWidget(delete_button)

        button_widget = QWidget()
        button_widget.setLayout(button_layout)
        self.output_table.setCellWidget(row_position, 2, button_widget)

    def handle_add_button_clicked(self):
        row_position = self.output_table.indexAt(self.sender().parent().pos()).row()
        self.add_row(row_position)

    def handle_delete_button_clicked(self):
        row_position = self.output_table.indexAt(self.sender().parent().pos()).row()
        self.delete_row(row_position)

    def delete_row(self, row_position):
        self.output_table.removeRow(row_position)

    def highlight_selected_section(self, section_name):
        # Find the section content
        lines = self.parsed_content.strip().split('\n')
        section_found = False
        content = []
        for line in lines:
            if line.startswith('['):
                if line.startswith(f"[{section_name}]"):
                    section_found = True
                elif section_found:
                    break
                else:
                    continue
            if section_found:
                content.append(line)
        if content:
            content = '\n'.join(content)
            # 在文本框内显示内容
            font = QFont("Microsoft YaHei UI", 13)
            self.gxt_path_entry.setFont(font)
            self.gxt_path_entry.setText(content)

    def filter_table(self, text):
        for row in range(self.output_table.rowCount()):
            key_item = self.output_table.item(row, 0)
            value_item = self.output_table.item(row, 1)
            if key_item and value_item and (text in key_item.text() or text in value_item.text()):
                self.output_table.showRow(row)
            else:
                self.output_table.hideRow(row)

    def scroll_to_section(self, idx, row_section_map):
        """根据下拉栏的选择定位到对应的表格行。"""
        section_name = self.section_combobox.itemText(idx)
        if section_name in row_section_map:
            row = row_section_map[section_name]
            self.output_table.scrollToItem(self.output_table.item(row, 0), QAbstractItemView.PositionAtTop)

def main():
    app = QApplication([])

    # 设置工作目录为脚本所在目录
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)

    window = GXTViewer()
    window.show()

    if len(sys.argv) == 2 and sys.argv[1].endswith(".gxt"):
        gxt_path = sys.argv[1]
        window.gxt_file_path = gxt_path
        window.open_gxt_path(gxt_path)

    app.exec_()

if __name__ == '__main__':
    main()
