import os
import errno
import gta.gxt
import ctypes
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGroupBox, QFileDialog,
    QMessageBox, QTableWidget, QTableWidgetItem, QLineEdit, QWidget, QComboBox, QAbstractItemView, QDialog, QHeaderView, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QRegExpValidator, QFont
import sys
import shutil
import subprocess
import re
import json
from PyQt5.QtNetwork import QNetworkRequest, QNetworkAccessManager

from master.about_window import open_about_window
from master.convert_using_table import convert_using_table
from master.check_update import UpdateChecker

APP_VERSION = "2.1.0"
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
        main_layout.setContentsMargins(15, 10, 15, 10)  # 减少边距
        main_layout.setSpacing(12)

        control_layout = QVBoxLayout()

        self.language_selector = QComboBox(self)
        for lang in self.available_languages:
            self.language_selector.addItem(lang)
        self.language_selector.setCurrentText('简体中文.lang')
        self.language_selector.currentIndexChanged.connect(self.change_language)
        control_layout.addWidget(self.language_selector)

        self.gxt_path_entry = QLineEdit(self)
        self.gxt_path_entry.setVisible(False)  # Hides the QLineEdit without affecting its functionality
        #control_layout.addWidget(self.gxt_path_entry)

        self.title_label = ClickableLabel("<h1>" + self.tr("window_title") + "</h1>")
        self.title_label.setOpenExternalLinks(True)
        self.title_label.setToolTip(self.tr("tooltip_browse_button"))
        self.title_label.clicked.connect(self.open_about_window)
        self.title_label.setStyleSheet("QLabel { color: #2c2c2c; }")
        control_layout.addWidget(self.title_label)

        button_groupbox = QGroupBox(self.tr("change_the_row"))
        button_layout = QHBoxLayout()
        button_container = QWidget()
        button_container.setObjectName("button_container")
        button_layout = QHBoxLayout(button_container)

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
        self.output_table.setColumnCount(3)
        self.output_table.setHorizontalHeaderLabels([self.tr("table_column_key"), self.tr("table_column_value"), self.tr("change_the_row")])
        self.output_table.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.output_table.verticalHeader().setVisible(False)
        self.output_table.setShowGrid(False)
        self.output_table.setColumnWidth(0, 150)  # 固定键列宽度
        self.output_table.setColumnWidth(2, 100)  # 操作列宽度
        self.output_table.verticalHeader().setDefaultSectionSize(32)  # 行高

        # 表格尺寸策略
        self.output_table.setSizePolicy(
            QSizePolicy.Expanding, 
            QSizePolicy.Expanding
        )
    
        # 滚动性能优化（修复版本）
        self.output_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.output_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)  # 平滑滚动
        self.output_table.setAlternatingRowColors(True)  # 交替行颜色提升可读性
        self.output_table.verticalHeader().setDefaultSectionSize(32)  # 原为24
        self.output_table.setMinimumHeight(300)
        self.output_table.setStyleSheet("""
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #EDF2F7;
            }
        """)
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

        lineedit_style = """
            QLineEdit {
                background: rgba(255,255,255,0.8);
                border: 1px solid #CBD5E0;
                border-radius: 6px;
                padding: 8px;
                selection-background-color: #90CDF4;
            }
            QLineEdit:focus {
                border: 2px solid #63B3ED;
                background: rgba(255,255,255,0.9);
            }
        """
        
        # 应用样式到所有输入框
        #self.search_entry = QLineEdit(self)
        #self.search_entry.setStyleSheet(lineedit_style)
        self.gxt_path_entry.setStyleSheet(lineedit_style)

        # 安装事件过滤器
        self.search_entry.installEventFilter(self)
        self.gxt_path_entry.installEventFilter(self)

    def eventFilter(self, obj, event):
        """处理双击透明度切换"""
        if event.type() == QtCore.QEvent.MouseButtonDblClick:
            if obj in [self.search_entry, self.gxt_path_entry]:
                current_style = obj.styleSheet()
                if "0.8" in current_style:
                    new_style = current_style.replace("0.8", "0.95")
                else:
                    new_style = current_style.replace("0.95", "0.8")
                obj.setStyleSheet(new_style)
                return True
        return super().eventFilter(obj, event)

    def safe_add_row(self, row):
        self.current_row = row

    def safe_delete_row(self, row):
        self.current_row = max(0, row-1)

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
        self.output_table.setHorizontalHeaderLabels([self.tr("table_column_key"), self.tr("table_column_value"), self.tr("change_the_row")])
        self.search_entry.setPlaceholderText(self.tr("search_placeholder"))

    def convert_using_table(self):
        convert_using_table(self)  # 确保传递完整实例

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
        
        # 性能优化：禁用UI更新和信号
        self.output_table.setUpdatesEnabled(False)
        self.output_table.blockSignals(True)
        self.output_table.clearContents()
        self.output_table.setRowCount(0)

        lines = content.splitlines()
        section_names = []
        table_data = []
        row_section_map = {}
        current_section = None
        row_index = 0

        # 优化1：预先创建字体对象
        font_normal = QFont("Microsoft YaHei UI", 10)
        font_bold = QFont("Microsoft YaHei UI", 10)
        font_bold.setBold(True)

        # 优化2：使用更高效的数据结构处理
        for line in lines:
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
                section_names.append(current_section)
                row_section_map[current_section] = row_index
                table_data.append(("section_marker", current_section, row_index))
                row_index += 1
            elif '=' in line:
                key, value = line.split('=', 1)
                table_data.append((key.strip(), value.strip(), row_index))
                row_index += 1

        # 优化3：预分配行数
        self.output_table.setRowCount(len(table_data))

        # 优化4：批量处理单元格数据
        for row, (key, value, _) in enumerate(table_data):
            # 处理段名行
            if key == "section_marker":
                item = QTableWidgetItem(f"[{value}]")
                item.setFlags(Qt.ItemIsEnabled)  # 段名行不可编辑
                item.setFont(font_bold)
                self.output_table.setItem(row, 0, item)
                self.output_table.setItem(row, 1, QTableWidgetItem(""))
            else:
                key_item = QTableWidgetItem(key)
                value_item = QTableWidgetItem(value)
                key_item.setFont(font_normal)
                value_item.setFont(font_normal)
                self.output_table.setItem(row, 0, key_item)
                self.output_table.setItem(row, 1, value_item)

            # 添加操作按钮
            self.add_row_buttons(row)

        # 设置段落下拉框
        self.section_combobox.clear()
        self.section_combobox.addItems(section_names)

        # 性能优化：恢复UI更新
        self.output_table.blockSignals(False)
        self.output_table.setUpdatesEnabled(True)
        self.output_table.viewport().update()

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
                QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_invalid_gxt_file_path"))
        else:
            QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_invalid_gxt_file_path"))

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
            QMessageBox.warning(self, self.tr("warning_messages"), self.tr("warning_select_and_parse_gxt_first"))
            return

        txt_file_path = QFileDialog.getSaveFileName(self, self.tr("save_as_txt"), os.path.splitext(self.gxt_txt_path)[0], "文本文件 (*.txt)")[0]
        if not txt_file_path:
            return

        try:
            with open(txt_file_path, 'w', encoding='utf-8') as target_file:
                target_file.write(self.parsed_content)
            QMessageBox.information(self, self.tr("prompt_messages"), self.tr("info_file_saved", path=txt_file_path))
        except Exception as e:
            QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_saving_file", error=str(e)))

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
            QMessageBox.warning(self, self.tr("warning_messages"), self.tr("warning_select_and_parse_gxt_first"))
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
            QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_unknown_gxt_version"))
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
            QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_unknown_gxt_version"))
            return

        builder_path = os.path.join("builder", builder_exe)
        debug_builder_path = os.path.join(debug_dir, builder_exe)

        if not os.path.isfile(builder_path):
            QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_builder_exe_not_found", exe=builder_exe))
            return

        shutil.copy(builder_path, debug_builder_path)

        # Run builder exe
        try:
            subprocess.run([debug_builder_path, output_txt_path], check=True, cwd=debug_dir)
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_running_builder", error=str(e)))
            return

        # Search for any .gxt file in the Debug directory and copy to original directory
        gxt_files = [f for f in os.listdir(debug_dir) if f.endswith('.gxt')]
        if gxt_files:
            # Assuming there's only one .gxt file generated
            generated_gxt_path = os.path.join(debug_dir, gxt_files[0])
            edited_gxt_path = os.path.join(gxt_dir, f"{os.path.splitext(os.path.basename(self.gxt_file_path))[0]}_Edited.gxt")
            shutil.copy(generated_gxt_path, edited_gxt_path)
            QMessageBox.information(self, self.tr("prompt_messages"), self.tr("info_gxt_saved", path=edited_gxt_path))
        else:
            QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_gxt_not_generated"))
        
    def safe_add_row(self, row):
        """带异常处理的新增行"""
        try:
            if 0 <= row < self.output_table.rowCount():
                self.output_table.insertRow(row + 1)
                # 初始化新行内容
                self.output_table.setItem(row+1, 0, CustomTableWidgetItem(self.tr("new_tkey")))
                self.output_table.setItem(row+1, 1, CustomTableWidgetItem(self.tr("new_tdat")))
                self.add_row_buttons(row+1)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加行失败: {str(e)}")

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

    def add_row_buttons(self, row):
        """优化后的按钮创建方法"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 0, 2, 0)  # 减少容器边距
        layout.setSpacing(10)  # 增加按钮间距到10px

        # 新样式配置
        btn_style = """
            QPushButton {{
                min-width: {size}px;
                max-width: {size}px;
                min-height: {size}px;
                max-height: {size}px;
                border-radius: 4px;
                font: bold 14px "Arial";
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:hover {{ background: {hover_color}; }}
            QPushButton:pressed {{ background: {press_color}; }}
        """
        
        # 调整按钮尺寸为24x24
        base_size = 20
        add_btn = QPushButton("+")
        add_btn.setStyleSheet(btn_style.format(
            size=base_size,
            hover_color="#81C784",  # 更柔和的绿色
            press_color="#4CAF50"    # 标准绿色
        ) + "background: #66BB6A; color: white;")  # 浅绿色背景
        
        del_btn = QPushButton("-")
        del_btn.setStyleSheet(btn_style.format(
            size=base_size,
            hover_color="#EF5350",  # 更柔和的红色
            press_color="#D32F2F"   # 标准红色
        ) + "background: #EF9A9A; color: white;")  # 浅红色背景

        # 添加按钮到布局
        layout.addWidget(add_btn)
        layout.addWidget(del_btn)
        
        # 设置按钮对齐方式
        layout.setAlignment(Qt.AlignCenter)

        # 安全绑定事件
        try:
            add_btn.clicked.disconnect()  # 先断开已有连接
        except:
            pass
        add_btn.clicked.connect(lambda: self.safe_add_row(row))
        
        try:
            del_btn.clicked.disconnect()
        except:
            pass
        del_btn.clicked.connect(lambda: self.safe_delete_row(row))
        
        layout.addWidget(add_btn)
        layout.addWidget(del_btn)
        
        self.output_table.setCellWidget(row, 2, widget)


    def handle_add_button_clicked(self):
        row_position = self.output_table.indexAt(self.sender().parent().pos()).row()
        self.add_row(row_position)

    def handle_delete_button_clicked(self):
        row_position = self.output_table.indexAt(self.sender().parent().pos()).row()
        self.delete_row(row_position)

    def safe_delete_row(self, row):
        """带安全检查的删除行"""
        try:
            if 0 <= row < self.output_table.rowCount():
                self.output_table.removeRow(row)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除行失败: {str(e)}")

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
            font = QFont("Microsoft YaHei UI", 10)
            self.gxt_path_entry.setFont(font)
            self.gxt_path_entry.setText(content)

    def filter_table(self, text):
        """优化后的过滤方法"""
        text = text.lower()
        for row in range(self.output_table.rowCount()):
            key_item = self.output_table.item(row, 0)
            value_item = self.output_table.item(row, 1)
            match = False
            
            if key_item and value_item:
                key = key_item.text().lower()
                value = value_item.text().lower()
                match = text in key or text in value
                
            self.output_table.setRowHidden(row, not match)

    def scroll_to_section(self, idx, row_section_map):
        """根据下拉栏的选择定位到对应的表格行。"""
        section_name = self.section_combobox.itemText(idx)
        if section_name in row_section_map:
            row = row_section_map[section_name]
            self.output_table.scrollToItem(self.output_table.item(row, 0), QAbstractItemView.PositionAtTop)

def main():
    
    def excepthook(exc_type, exc_value, exc_tb):
        import traceback
        msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        QMessageBox.critical(None, "未捕获异常", msg)
        sys.exit(1)

    sys.excepthook = excepthook
    
    app = QApplication([])

    app.setApplicationVersion(APP_VERSION)

    app.setStyleSheet("""
        /* ========== 基础框架样式 ========== 
        设计目标：建立统一的视觉基线和呼吸感 */
        QWidget {
            background: #F8FAFC;  /* 主背景色-浅灰蓝 */
            color: #2D3748;       /* 主文字色-深灰 */
            font-family: 'Microsoft YaHei UI', 'Microsoft YaHei'; /* 字体优先使用系统默认 */
            font-size: 13px;      /* 基准字号保持可读性 */
            border: none;         /* 清除默认边框 */
        }

        /* ========== 标题文字样式 ==========
        设计目标：突出品牌色，建立视觉层次 */
        QLabel[titleRole="true"] {
            font: 600 24px 'Segoe UI'; /* 加粗大标题 */
            color: #2B6CB0;        /* 品牌主色-深蓝 */
            padding: 20px 0;       /* 上下留白增强呼吸感 */
            qproperty-alignment: AlignCenter; /* 居中显示 */
        }

        /* ========== 功能按钮组容器 ==========
        设计目标：创建内容区块的视觉分割 */
        QGroupBox {
            border: 1px solid #E2E8F0; /* 浅灰色边框 */
            border-radius: 8px;    /* 圆角匹配现代风格 */
            margin-top: 16px;      /* 与上方元素保持间距 */
            padding-top: 0px;     /* 标题下留白 */
            background: white;     /* 纯白背景突出内容 */
        }

        /* 组标题样式 */
        QGroupBox::title {
            color: #4A5568;        /* 中灰色文字 */
            subcontrol-origin: margin; /* 定位基准 */
            left: 12px;            /* 左对齐偏移 */
            padding: 0 3px;       /* 文字内边距 */
        }

        /* ========== 主要操作按钮 ==========
        设计目标：强调核心操作，提供明确反馈 */
        QPushButton {
            background: #4299E1;   /* 品牌蓝色 */
            color: white;          /* 高对比文字 */
            border-radius: 10px;    /* 统一圆角 */
            padding: 8px 16px;     /* 舒适点击区域 */
            min-width: 90px;       /* 保证按钮宽度一致 */
            transition: background 0.7s; /* 平滑状态过渡 */
        }
        /* 悬停状态 - 颜色加深10% */
        QPushButton:hover { background: #3182CE; }
        /* 按下状态 - 颜色加深20% */
        QPushButton:pressed { background: #2B6CB0; }
        /* 禁用状态 - 灰化处理 */
        QPushButton:disabled {
            background: #CBD5E0;   /* 浅灰色 */
            color: #718096;        /* 中灰色文字 */
        }

        /* ========== 输入控件 ==========
        设计目标：清晰的可交互状态指示 */
        QLineEdit, QComboBox {
            border: 2px solid #E2E8F0; /* 默认边框色 */
            border-radius: 10px;    /* 匹配按钮圆角 */
            padding: 8px 12px;     /* 舒适输入区域 */
            background: white;     /* 纯白背景 */
            min-height: 24px;      /* 统一控件高度 */
        }
        /* 聚焦/悬停状态 - 高亮边框 */
        QLineEdit:focus, QComboBox:hover {
            border-color: #90CDF4; /* 浅蓝色反馈 */
        }

        /* ========== 数据表格 ==========
        设计目标：提升数据可读性，减少视觉疲劳 */
        QTableWidget {
            background: white;     /* 纯白背景 */
            border: 1px solid #E2E8F0; /* 浅灰边框 */
            border-radius: 10px;    /* 统一圆角 */
            gridline-color: #EDF2F7; /* 浅网格线 */
            alternate-background-color: #F7FAFC; /* 交替行背景色 */
        }
        /* 表头样式 */
        QHeaderView::section {
            background: #EBF8FF;   /* 浅蓝背景 */
            color: #2C5282;        /* 深蓝文字 */
            padding: 12px;         /* 表头内边距 */
            border: none;          /* 清除默认边框 */
            font-weight: 600;      /* 加粗突出 */
        }
        /* 单元格样式 */
        QTableWidget::item {
            padding: 10px;         /* 单元格内边距 */
            border-bottom: 1px solid #EDF2F7; /* 下划线分隔 */
        }

        /* ========== 下拉菜单 ========== */
        QComboBox::drop-down {
            width: 24px;           /* 箭头区域宽度 */
            border-left: 2px solid #E2E8F0; /* 分割线 */
        }
        /* 下拉项样式 */
        QComboBox QAbstractItemView {
            border: 0px solid #E2E8F0; /* 悬浮边框 */
            selection-background-color: #BEE3F8; /* 选中项高亮 */
        }

        /* ========== 滚动条 ==========
        设计目标：保持功能可见性同时最小化视觉干扰 */
        QScrollBar:vertical {
            background: #F1F5F9;   /* 轨道背景色 */
            width: 15px;           /* 窄幅设计 */
            margin: 2px;           /* 外边距 */
        }
        /* 滚动条手柄 */
        QScrollBar::handle:vertical {
            background: #CBD5E0;   /* 中灰色 */
            border-radius:5px;    /* 圆角设计 */
            min-height: 50px;      /* 最小高度 */
        }
       /* 表格选中状态 */
        QTableView::item:selected {
            background: #90CDF4;
            color: #1A202C;
            border: none;
        }

        /* 滚动条箭头样式 */
        QScrollBar::up-arrow, QScrollBar::down-arrow {
            background: none;
            border: none;
            color: #718096;
        }
        
        QScrollBar::add-line, QScrollBar::sub-line {
            background: #E2E8F0;
            border: 1px solid #CBD5E0;
            height: 20px;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            width: 20px;
        }
        /* ========== 操作按钮 ==========
            /* 确保按钮文字居中 */
        QPushButton {
            qproperty-alignment: AlignCenter;
        }
        
        /* 移除单元格聚焦边框 */
        QTableWidget::item:focus {
            border: none;
            outline: none;
        }
        /* ========== 检查更新 ==========
            /* 更新提示对话框 */
        QMessageBox {
            background: #FFFFFF;
            font-size: 14px;
        }
        QMessageBox QLabel {
            color: #2D3748;
            line-height: 1.6;
        }
        QMessageBox QPushButton {
            min-width: 80px;
            padding: 6px 12px;
            margin: 8px;
        }
    """)
    # 设置工作目录为脚本所在目录
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)

    window = GXTViewer()
    window.show()

    def handle_update(new_version, release_url, message):
        title = window.tr("update_available_title")
        # 尝试翻译并格式化版本提示
        try:
            base_msg = window.tr("update_available_msg").format(
                new_version=new_version,
                current_version=APP_VERSION
            )
        except Exception:
            base_msg = f"检测到新版本 {new_version}\n当前版本 {APP_VERSION}，是否前往下载？"

        # 将 message 字段放在第二行（如果不为空）
        if message:
            # 注意：这里用 '\n' 换行
            base_msg = f"{base_msg}\n{message}"

        reply = QMessageBox.question(
            window,
            title,
            base_msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            import webbrowser
            webbrowser.open(release_url)

    def handle_error(error_msg):
        # 使用应用程序的activeWindow()而不是直接引用window
        QMessageBox.warning(QApplication.activeWindow(), 
                          "Update Error", 
                          f"检查更新失败: {error_msg}")
        
    checker = UpdateChecker(APP_VERSION)
    checker.update_available.connect(handle_update)
    checker.error_occurred.connect(handle_error)
    checker.check()  # 启动异步检查


    if len(sys.argv) == 2 and sys.argv[1].endswith(".gxt"):
        gxt_path = sys.argv[1]
        window.gxt_file_path = gxt_path
        window.open_gxt_path(gxt_path)

    app.exec_()

if __name__ == '__main__':
    main()
