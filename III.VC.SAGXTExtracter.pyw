import os
import errno
import gta.gxt
import ctypes
from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGroupBox, QFileDialog,
    QMessageBox, QTableWidget, QTableWidgetItem, QLineEdit, QWidget, QComboBox, QAbstractItemView, QDialog, QHeaderView, QSizePolicy,
    QStyledItemDelegate, QMenu, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QRegularExpressionValidator, QFont, QTextDocument, QColor, QAction

# 兼容PyQt6的SectionResizeMode写法
from PyQt6.QtWidgets import QHeaderView
SectionResizeMode = QHeaderView.ResizeMode

import sys
import shutil
import subprocess
import re
import json
from PyQt6.QtNetwork import QNetworkRequest, QNetworkAccessManager

from master.about_window import open_about_window
from master.convert_using_table import convert_using_table
from master.check_update import UpdateChecker
from debug.debug_menu import DebugMenu

def show_copyable_error(parent, title, text):
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setMinimumWidth(520)
    layout = QVBoxLayout(dlg)
    label = QLabel(title)
    label.setStyleSheet("font-weight:bold;font-size:15px;")
    layout.addWidget(label)
    edit = QTextEdit()
    edit.setReadOnly(False)  # 可编辑
    edit.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
    edit.setText(text)
    edit.setStyleSheet("font-family: Consolas, 'Courier New', monospace; font-size: 13px;")
    layout.addWidget(edit)
    btn = QPushButton("关闭")
    btn.clicked.connect(dlg.accept)
    layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight)
    dlg.setModal(True)
    dlg.exec()

APP_VERSION = "2.3.0"
myappid = "III.VC.SAGXTExtracter"
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

class ClickableLabel(QLabel):
    clicked = QtCore.pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()

class CustomTableWidgetItem(QTableWidgetItem):
    def __init__(self, text=""):
        super().__init__(text)
        self.setFlags(self.flags() | Qt.ItemFlag.ItemIsEditable)  # 修正命名空间

class GXTViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.gxt_file_path = None
        self.gxt_txt_path = None
        self.parsed_content = ""
        self.translations = {}
        self._row_cache = None  # 新增：缓存表格行数据
        self.debug_menu = DebugMenu(self)
        self._table_hover_filter = None  # 防止未定义
        self.section_buttons = []  # 初始化section_buttons属性
        self.regex_mode = False  # 添加正则表达式模式标志
        self.load_language_file()
        self.initUI()
        self.installEventFilter(self)  # 用于全局快捷键

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

    def tr(self, key: str, **kwargs) -> str:
        """Helper function to retrieve translated text and format it."""
        if not key:
            return ""
        translation = self.translations.get(str(key), str(key))
        return translation.format(**kwargs)

    def initUI(self):
        self.load_available_languages()
        self.setWindowIcon(QIcon('./favicon.ico'))
        self.setWindowTitle(self.tr("window_title"))
        self.resize(960, 618)
        
        # 添加搜索防抖定时器
        self.search_timer = QtCore.QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        self.search_cache = {}  # 搜索缓存
        self.table_data_cache = []  # 表格数据缓存
        self.regex_mode = False  # 添加正则表达式模式标志

        font = QtGui.QFont("Microsoft YaHei UI", 10)
        app = QApplication.instance()
        if app is not None:
            QApplication.setFont(font)  # PyQt6使用静态方法

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 10, 15, 10)
        main_layout.setSpacing(12)

        control_layout = QVBoxLayout()

        self.language_selector = QComboBox(self)
        for lang in self.available_languages:
            self.language_selector.addItem(lang)
        self.language_selector.setCurrentText('简体中文.lang')
        self.language_selector.currentIndexChanged.connect(self.change_language)
        control_layout.addWidget(self.language_selector)

        self.gxt_path_entry = QLineEdit(self)
        self.gxt_path_entry.setVisible(False)
        #control_layout.addWidget(self.gxt_path_entry)

        self.title_label = ClickableLabel("<h1>" + self.tr("window_title") + "</h1>")
        self.title_label.setOpenExternalLinks(True)
        self.title_label.setToolTip(self.tr("tooltip_title"))
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
        self.browse_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 12px; padding: 5px; min-width: 100px; min-height: 28px; font-size: 14px; font-weight: bold; }")
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(2)
        shadow.setOffset(1, 1)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.browse_button.setGraphicsEffect(shadow)
        self.browse_button.setToolTip(self.tr("tooltip_browse_button"))
        button_layout.addWidget(self.browse_button)

        self.convert_button = QPushButton(self.tr("convert_button_text"), self)
        self.convert_button.clicked.connect(self.convert_using_table)
        self.convert_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 12px; padding: 5px; min-width: 100px; min-height: 28px; font-size: 14px; font-weight: bold; }")
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(2)
        shadow.setOffset(1, 1)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.convert_button.setGraphicsEffect(shadow)
        self.convert_button.setToolTip(self.tr("tooltip_convert_button"))
        button_layout.addWidget(self.convert_button)

        self.save_button = QPushButton(self.tr("save_button_text"), self)
        self.save_button.clicked.connect(self.save_generated_txt)
        self.save_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 12px; padding: 5px; min-width: 100px; min-height: 28px; font-size: 14px; font-weight: bold; }")
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(2)
        shadow.setOffset(1, 1)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.save_button.setGraphicsEffect(shadow)
        self.save_button.setToolTip(self.tr("tooltip_save_button"))
        button_layout.addWidget(self.save_button)

        self.clear_button = QPushButton(self.tr("clear_button_text"), self)
        # self.clear_button.clicked.connect(self.clear_table)
        self.clear_button.clicked.connect(self.smart_translate_table)
        self.clear_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 12px; padding: 5px; min-width: 100px; min-height: 28px; font-size: 14px; font-weight: bold; }")
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(2)
        shadow.setOffset(1, 1)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.clear_button.setGraphicsEffect(shadow)
        self.clear_button.setToolTip(self.tr("tooltip_clear_button"))
        button_layout.addWidget(self.clear_button)

        self.save_gxt_button = QPushButton(self.tr("save_gxt_button_text"), self)
        self.save_gxt_button.clicked.connect(self.save_and_build_gxt)
        self.save_gxt_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 12px; padding: 5px; min-width: 100px; min-height: 28px; font-size: 14px; font-weight: bold; }")
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(2)
        shadow.setOffset(1, 1)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.save_gxt_button.setGraphicsEffect(shadow)
        self.save_gxt_button.setToolTip(self.tr("tooltip_save_gxt_button"))
        button_layout.addWidget(self.save_gxt_button)

        button_groupbox.setLayout(button_layout)
        control_layout.addWidget(button_groupbox)

        main_layout.addLayout(control_layout)

        # 创建水平布局以容纳侧边栏和表格
        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)
        
        # 创建侧边栏部件
        self.sidebar = QGroupBox(self.tr("section_sidebar_title"))
        self.sidebar.setStyleSheet("""
            QGroupBox {
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                margin-top: 16px;
                padding-top: 10px;
                background: white;
                min-width: 180px;
                max-width: 250px;
                height: 100%;
            }
            QGroupBox::title {
                color: #4A5568;
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 3px;
            }
        """)
        
        # 创建侧边栏布局
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(5, 5, 5, 5)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 创建侧边栏按钮区域
        self.sidebar_widget = QtWidgets.QWidget()
        self.sidebar_layout = QVBoxLayout(self.sidebar_widget)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.sidebar_layout.setSpacing(1)
        
        # 添加滚动区域以容纳大量section
        self.sidebar_scroll = QtWidgets.QScrollArea()
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setWidget(self.sidebar_widget)
        self.sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #F1F5F9;
                width: 10px;
                border-radius: 5px;
                margin: 2px 0 2px 0;
            }
            QScrollBar::handle:vertical {
                background: #BFD7ED;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #7BA7D7;
            }
        """)
        
        sidebar_layout.addWidget(self.sidebar_scroll)
        self.sidebar.setLayout(sidebar_layout)
        
        # 添加侧边栏到内容布局
        content_layout.addWidget(self.sidebar, 1)
        
        # 创建右侧内容区域布局
        right_content_layout = QVBoxLayout()
        right_content_layout.setSpacing(10)

        # 下拉栏统一美工样式
        combo_style = """
            QComboBox {
                font-size: 13px;
                min-height: 24px;
                min-width: 200px;
                padding: 6px 32px 6px 12px;
                border: 2px solid #90CDF4;
                border-radius: 10px;
                background: #F7FAFC;
                color: #2B6CB0;
                selection-background-color: #BEE3F8;
                selection-color: #1A365D;
            }
            QComboBox:focus {
                border: 2px solid #4299E1;
                background: #E3F2FD;
            }
            QComboBox::drop-down {
                width: 32px;
                border-left: 1px solid #BEE3F8;
                background: #E3F2FD;
                subcontrol-origin: padding;
                subcontrol-position: top right;
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
            }
            QComboBox::down-arrow {
                image: url(:/qt-project.org/styles/commonstyle/images/arrowdown-16.png);
                width: 18px;
                height: 18px;
            }
            QComboBox QAbstractItemView {
                font-size: 13px;
                background: #FFFFFF;
                selection-background-color: #BEE3F8;
                selection-color: #1A365D;
                border: 1px solid #90CDF4;
                outline: none;
                padding: 4px 0;
                border-radius: 10px; /* 统一圆角 */
            }
        """

        self.language_selector.setStyleSheet(combo_style)
        self.language_selector.setMinimumWidth(220)
        self.language_selector.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

        self.output_table = QTableWidget(self)
        self.output_table.setColumnCount(3)
        self.output_table.setHorizontalHeaderLabels([self.tr("table_column_key"), self.tr("table_column_value"), self.tr("change_the_row")])
        # 修改为PyQt6的EditTrigger
        self.output_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        vh = self.output_table.verticalHeader()
        if vh is not None:
            vh.setVisible(True)  # 显示行号
            vh.setDefaultAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            vh.setSectionResizeMode(SectionResizeMode.Fixed)
            vh.setDefaultSectionSize(32)
            vh.setMinimumWidth(32)
            vh.setMaximumWidth(40)
            vh.setStyleSheet("""
                QHeaderView::section {
                    background: #F7FAFC;
                    color: #888;
                    font: 12px 'Consolas', 'Menlo', 'Monaco', 'Microsoft YaHei UI';
                    border: none;
                    padding-right: 6px;
                    padding-left: 0px;
                    border-radius: 0px;
                }
            """)
        self.output_table.setShowGrid(False)
        self.output_table.setColumnWidth(0, 150)  # 固定键列宽度
        self.output_table.setColumnWidth(2, 100)  # 操作列宽度
        v_header = self.output_table.verticalHeader()
        if v_header is not None:
            try:
                v_header.setDefaultSectionSize(32)
            except AttributeError as e:
                print(f"Error setting vertical header size: {e}")

        # 表格尺寸策略
        self.output_table.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Expanding
        )
    
        # 滚动性能优化（修复版本）
        header = self.output_table.horizontalHeader()
        if header is not None:
            try:
                header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            except AttributeError as e:
                print(f"Error setting header resize mode: {e}")
                # Fallback to default behavior
                header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.output_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)  # 平滑滚动
        self.output_table.setAlternatingRowColors(True)  # 交替行颜色提升可读性
        v_header = self.output_table.verticalHeader()
        if v_header is not None:
            try:
                v_header.setDefaultSectionSize(32)
            except AttributeError as e:
                print(f"Error setting vertical header size: {e}")
        self.output_table.setMinimumHeight(300)
        self.output_table.setStyleSheet("""
            QTableWidget {
                border-radius: 12px;
                border: 1px solid #E2E8F0;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #EDF2F7;
            }
        """)
        # 将表格添加到右侧内容布局
        right_content_layout.addWidget(self.output_table)

        # 获取表格的头部并设置列宽
        header = self.output_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, SectionResizeMode.Fixed)
            header.setSectionResizeMode(1, SectionResizeMode.Stretch)
            header.setSectionResizeMode(2, SectionResizeMode.Fixed)
            # 设置固定宽度
            self.output_table.setColumnWidth(0, 100)  # 第一列宽度固定，适合8个字符
            self.output_table.setColumnWidth(2, 80)  # 第三列宽度固定，适合按钮

        # 第二列宽度会随窗口大小变化
        # 创建包含搜索框和正则表达式按钮的水平布局
        search_layout = QHBoxLayout()
        self.search_entry = QLineEdit(self)
        self.search_entry.setPlaceholderText(self.tr("search_placeholder"))
        # 使用防抖机制而不是直接连接到filter_table
        self.search_entry.textChanged.connect(self.schedule_search)
        # 确保搜索框与正则表达式按钮高度一致
        self.search_entry.setFixedHeight(32)
        
        # 创建正则表达式切换按钮
        self.regex_button = QPushButton(".*", self)
        self.regex_button.setCheckable(True)
        self.regex_button.setFixedSize(32, 32)  # 设置固定尺寸为32x32
        self.regex_button.setToolTip(self.tr("toggle_regex_mode"))
        self.regex_button.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #CBD5E0;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                padding: 0px;
            }
            QPushButton:checked {
                background-color: #4299E1;
                color: white;
                border: 1px solid #4299E1;
            }
        """)
        self.regex_button.clicked.connect(self.toggle_regex_mode)
        
        search_layout.addWidget(self.search_entry)
        search_layout.addWidget(self.regex_button)
        # 设置布局中的对齐方式，确保垂直居中
        search_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # 将搜索框添加到右侧内容布局底部
        right_content_layout.addLayout(search_layout)
        
        # 将右侧内容区域添加到内容布局
        content_layout.addLayout(right_content_layout, 4)
        
        # 将内容布局添加到主布局
        main_layout.addLayout(content_layout)

        self.setLayout(main_layout)
        self.setAcceptDrops(True)

        lineedit_style = """
            QLineEdit {
                background: rgba(255,255,255,0.8);
                border: 1px solid #CBD5E0;
                border-radius: 6px;
                padding: 4px 8px;  /* 减少垂直内边距以适应32px高度 */
                selection-background-color: #90CDF4;
            }
            QLineEdit:focus {
                border: 2px solid #63B3ED;
                background: rgba(255,255,255,0.9);
            }
        """
        
        # 应用样式到所有输入框
        self.search_entry.setStyleSheet(lineedit_style)
        self.gxt_path_entry.setStyleSheet(lineedit_style)

        # 安装事件过滤器
        self.search_entry.installEventFilter(self)
        self.gxt_path_entry.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.MouseButtonDblClick:
            if obj in [self.search_entry, self.gxt_path_entry]:
                current_style = obj.styleSheet()
                if "0.8" in current_style:
                    new_style = current_style.replace("0.8", "0.95")
                else:
                    new_style = current_style.replace("0.95", "0.8")
                obj.setStyleSheet(new_style)
                return True
        if event.type() == QtCore.QEvent.Type.KeyPress:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_M:
                # 修复：直接调用debug_menu的show_menu方法
                if hasattr(self, 'debug_menu') and self.debug_menu:
                    # 忽略IDE的误报，DebugMenu类确实有show_menu方法
                    self.debug_menu.show_menu()  # type: ignore
                return True
        return super().eventFilter(obj, event)

    def show_debug_menu(self):
        if self.debug_menu is None:
            self.debug_menu = QMenu(self)
            # 多功能调试菜单项
            action_print_table = QAction("打印当前表格内容", self)
            action_print_table.triggered.connect(self.debug_print_table)
            self.debug_menu.addAction(action_print_table)

            action_reload_lang = QAction("重载语言文件", self)
            action_reload_lang.triggered.connect(self.debug_reload_language)
            self.debug_menu.addAction(action_reload_lang)

            action_show_gxt_path = QAction("显示当前GXT路径", self)
            action_show_gxt_path.triggered.connect(self.debug_show_gxt_path)
            self.debug_menu.addAction(action_show_gxt_path)

            action_show_version = QAction("显示窗口标题/版本", self)
            action_show_version.triggered.connect(self.debug_show_version)
            self.debug_menu.addAction(action_show_version)

            action_dummy = QAction("（预留功能）", self)
            action_dummy.setEnabled(False)
            self.debug_menu.addAction(action_dummy)
        # 居中弹出菜单
        pos = self.mapToGlobal(self.rect().center())
        # 只允许QMenu弹出
        if isinstance(self.debug_menu, QMenu):
            self.debug_menu.exec(pos)

    def debug_print_table(self):
        # 打印当前表格内容到控制台
        rows = self.output_table.rowCount()
        cols = self.output_table.columnCount()
        print("=== 当前表格内容 ===")
        for r in range(rows):
            row_data = []
            for c in range(cols):
                item = self.output_table.item(r, c)
                row_data.append(item.text() if item else "")
            print(f"Row {r}: {row_data}")

    def debug_reload_language(self):
        # 重新加载当前语言
        selected_lang = self.language_selector.currentText()
        lang_file_path = os.path.join('languages', selected_lang)
        self.load_language_file(lang_file_path)
        self.update_ui_texts()
        QMessageBox.information(self, self.tr("debug_title"), self.tr("debug_lang_reloaded"))

    def debug_show_gxt_path(self):
        # 显示当前GXT文件路径
        QMessageBox.information(self, self.tr("debug_title"), self.tr("debug_gxt_path", path=self.gxt_file_path))

    def debug_show_version(self):
        # 显示窗口标题/版本
        QMessageBox.information(self, self.tr("debug_title"), self.tr("debug_window_info", title=self.windowTitle(), version=APP_VERSION))

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
        self.regex_button.setToolTip(self.tr("toggle_regex_mode"))
        # 更新侧边栏标题
        self.sidebar.setTitle(self.tr("section_sidebar_title"))

    def convert_using_table(self):
        convert_using_table(self)  # 确保传递完整实例

    def readOutTable(self, gxt, reader, name: str, outDirName: str):
        output_file_path = os.path.join(outDirName, name + '.txt')
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(f'[{name}]\n')
            if reader is not None and hasattr(reader, "parseTKeyTDat"):
                for text in reader.parseTKeyTDat(gxt):
                    f.write(text[0] + '=' + text[1] + '\n')

    @staticmethod
    def createOutputDir(path: str):
        try:
            os.makedirs(path)
            # 仅对Debug文件夹设置隐藏属性
            if "Debug" in path:
                ctypes.windll.kernel32.SetFileAttributesW(path, 2)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def gxt_processing(self, file_path: str, outDirName: str, render_only=False):
        import time
        gxt_name = os.path.splitext(os.path.basename(file_path))[0]
        try:
            start_time = time.perf_counter()
            with open(file_path, 'rb') as gxt:
                gxtversion = gta.gxt.getVersion(gxt)
                if not gxtversion:
                    QMessageBox.critical(self, self.tr("error"), self.tr("error_unknown_gxt_version"))
                    return ""
                current_title = self.windowTitle()
                new_title = self.tr("title_version") + " " + gxtversion
                self.setWindowTitle(new_title)

                gxtReader = gta.gxt.getReader(gxtversion)
                if gxtReader is None:
                    QMessageBox.critical(self, self.tr("error"), self.tr("error_unknown_gxt_version"))
                    return ""

                content_lines = []
                if gxtversion == 'III':
                    if hasattr(gxtReader, "parseTKeyTDat"):
                        for text in gxtReader.parseTKeyTDat(gxt):
                            # 修正：保留所有内容，包括最后一个字符
                            content_lines.append(f"{text[0]}={text[1]}")
                    content_str = "\n".join(content_lines)
                    if not render_only:
                        self.gxt_txt_path = os.path.join(os.path.dirname(file_path), f"{gxt_name}.txt")
                        with open(self.gxt_txt_path, 'w', encoding='utf-8') as output_file:
                            output_file.write(content_str)
                else:
                    gxt_dir = os.path.join(os.path.dirname(file_path), gxt_name)
                    if not render_only:
                        self.createOutputDir(gxt_dir)
                    Tables = []
                    if hasattr(gxtReader, "hasTables") and gxtReader.hasTables() and hasattr(gxtReader, "parseTables"):
                        Tables = gxtReader.parseTables(gxt)
                    all_table_content = []
                    for table_name, _ in Tables:
                        table_lines = [f"[{table_name}]"]
                        if hasattr(gxtReader, "parseTKeyTDat"):
                            for text in gxtReader.parseTKeyTDat(gxt):
                                # 修正：保留所有内容，包括最后一个字符
                                table_lines.append(f"{text[0]}={text[1]}")
                        all_table_content.append("\n".join(table_lines))
                        if not render_only:
                            table_file_path = os.path.join(gxt_dir, f"{table_name}.txt")
                            with open(table_file_path, 'w', encoding='utf-8') as table_file:
                                table_file.write("\n".join(table_lines))
                    content_str = "\n\n".join(all_table_content)
                    if not render_only:
                        self.gxt_txt_path = os.path.join(os.path.dirname(file_path), f"{outDirName}.txt")
                        with open(self.gxt_txt_path, 'w', encoding='utf-8') as output_file:
                            output_file.write(content_str)

                elapsed = time.perf_counter() - start_time
                self.setWindowTitle(f"{self.tr('title_version')} {gxtversion} | {elapsed:.3f}s")
                return content_str
        except Exception as e:
            QMessageBox.critical(self, self.tr("error"), self.tr("error_opening_gxt_file", error=str(e)))
            return ""

    def open_gxt_file(self, file_path: str):
        if os.path.isfile(file_path) and file_path.lower().endswith(".gxt"):
            self.gxt_file_path = file_path
            outDirName = os.path.splitext(os.path.basename(file_path))[0]
            # 优先解析并渲染表格
            content_str = self.gxt_processing(file_path, outDirName, render_only=True)
            self.output_table.clearContents()
            if content_str:
                self.display_gxt_content_in_table(content_str)
                # 文件生成延后，异步或后台生成
                QtCore.QTimer.singleShot(0, lambda: self.gxt_processing(file_path, outDirName, render_only=False))
            else:
                QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_invalid_gxt_file_path"))
        else:
            QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_invalid_gxt_file_path"))

    def open_txt_file(self, file_path: str):
        """支持直接打开txt文件并渲染到表格，自动校验格式错误"""
        if os.path.isfile(file_path) and file_path.lower().endswith(".txt"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # 校验格式
                error_lines = []
                lines = content.split('\n')
                for idx, line in enumerate(lines):
                    if not line.strip():
                        continue
                    if line.startswith('[') and line.endswith(']'):
                        continue
                    if '=' not in line:
                        error_lines.append(idx + 1)
                if error_lines:
                    QMessageBox.critical(self, self.tr("error_txt_format"), self.tr("error_missing_equals", lines=', '.join(map(str, error_lines))))
                    return
                self.gxt_file_path = None
                self.gxt_txt_path = file_path
                self.display_gxt_content_in_table(content)
            except Exception as e:
                QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_opening_gxt_file", error=str(e)))
        else:
            QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_invalid_gxt_file_path"))

    def select_gxt_file(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(self, self.tr("select_gxt_file"), "", "GXT文件 (*.gxt);;文本文件 (*.txt)")
            if file_path:
                self.gxt_path_entry.clear()
                self.gxt_path_entry.setText(file_path)
                if file_path.lower().endswith('.gxt'):
                    self.open_gxt_file(file_path)
                elif file_path.lower().endswith('.txt'):
                    self.open_txt_file(file_path)
        except Exception as e:
            print("Error:", e)

    def open_gxt_from_input(self):
        file_path = self.gxt_path_entry.text()
        if file_path.lower().endswith('.gxt'):
            self.open_gxt_file(file_path)
        elif file_path.lower().endswith('.txt'):
            self.open_txt_file(file_path)

    def save_generated_txt(self):
        if self.output_table.rowCount() == 0:
            QMessageBox.warning(self, self.tr("warning_messages"), self.tr("warning_select_and_parse_gxt_first"))
            return

        txt_file_path, _ = QFileDialog.getSaveFileName(self, self.tr("save_as_txt"), os.path.splitext(self.gxt_txt_path or "")[0], "文本文件 (*.txt)")
        if not txt_file_path:
            return

        try:
            content = []
            current_section = ""
            
            for row in range(self.output_table.rowCount()):
                key_item = self.output_table.item(row, 0)
                value_item = self.output_table.item(row, 1)
                
                if key_item and value_item:
                    key = key_item.text()
                    value = value_item.text()
                    
                    if key.startswith('[') and key.endswith(']'):
                        current_section = key
                        content.append(key)
                    else:
                        content.append(f"{key}={value}")
            
            with open(txt_file_path, 'w', encoding='utf-8') as target_file:
                target_file.write("\n".join(content))
            
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
            if url.isLocalFile() and (url.toLocalFile().lower().endswith(".gxt") or url.toLocalFile().lower().endswith(".txt")):
                event.acceptProposedAction()

    def dropEvent(self, event):
        url = event.mimeData().urls()[0]
        file_path = url.toLocalFile()
        if file_path.lower().endswith('.gxt'):
            self.open_gxt_file(file_path)
        elif file_path.lower().endswith('.txt'):
            self.open_txt_file(file_path)

    def save_and_build_gxt(self):
        # 检查gxt_file_path是否为空，如果是txt导入，则用txt路径所在目录
        if self.gxt_file_path:
            gxt_dir = os.path.dirname(self.gxt_file_path)
        elif self.gxt_txt_path:
            gxt_dir = os.path.dirname(self.gxt_txt_path)
        else:
            QMessageBox.warning(self, self.tr("warning_messages"), self.tr("warning_select_and_parse_gxt_first"))
            return

        debug_dir = os.path.join(gxt_dir, "Debug")

        if os.path.exists(debug_dir):
            shutil.rmtree(debug_dir)
        self.createOutputDir(debug_dir)

        # 判断版本
        version = None
        auto_detected_version = None
        if self.gxt_file_path:
            try:
                with open(self.gxt_file_path, 'rb') as gxt:
                    version = gta.gxt.getVersion(gxt)
            except Exception:
                pass
            if not version:
                title = self.windowTitle()
                for v in ['III', 'VC', 'SA', 'IV']:
                    if v in title:
                        version = v
                        break
        else:
            # txt导入时，尝试根据txt内容自动识别版本，并让用户选择
            version = None
            auto_detected_version = None
            if self.gxt_txt_path:
                try:
                    with open(self.gxt_txt_path, 'r', encoding='utf-8') as f:
                        txt_content = f.read()
                    lines = [line.strip() for line in txt_content.splitlines() if line.strip()]
                    sections = [line for line in lines if line.startswith("[") and line.endswith("]")]
                    keys = [line for line in lines if '=' in line and not (line.startswith("[") and line.endswith("]"))]
                    section_names = set(s.lower() for s in sections)
                    # 1. 没有section，且全部为key=value，极大概率为GTA3（III）
                    if not sections:
                        auto_detected_version = "III"
                    else:
                        # 2. 有section，分析section名和key格式
                        import re
                        vc_section_re = re.compile(r"^\[[0-9A-Z_]{1,7}\]$")
                        vc_key_re = re.compile(r"^[0-9A-Z_]{1,7}$")
                        sa_section_re = re.compile(r"^\[[A-Z_]{1,7}\]$")  # SA表名只能大写字母和下划线
                        sa_key_re = re.compile(r"^[0-9A-F]{8}$", re.IGNORECASE)
                        iv_section_re = re.compile(r"^\[[0-9A-Za-z_]{1,7}\]$")  # IV表名可有小写
                        # 检查所有section和key是否符合VC、SA、IV格式
                        is_vc = all(vc_section_re.match(s) for s in sections) and all(vc_key_re.match(k.split('=')[0]) for k in keys)
                        is_sa = all(sa_section_re.match(s) for s in sections) and all(sa_key_re.match(k.split('=')[0]) for k in keys)
                        is_iv = all(iv_section_re.match(s) for s in sections) and all(sa_key_re.match(k.split('=')[0]) for k in keys)
                        if is_sa:
                            # 优化：如果所有section都是大写字母和下划线，提示“识别为SA/IV”
                            auto_detected_version = "SA"
                            if all(sa_section_re.match(s) for s in sections):
                                auto_detected_version = "SA/IV"
                        elif is_vc:
                            auto_detected_version = "VC"
                        elif is_iv:
                            auto_detected_version = "IV"
                        elif "[main]" in section_names and len(section_names) == 1:
                            # 只有[MAIN]，进一步判断key格式
                            crc32_key = re.compile(r"^[0-9A-Fa-f]{8}$")
                            key_samples = [k.split('=')[0].strip() for k in keys[:10]]
                            if all(crc32_key.match(k) for k in key_samples if k):
                                auto_detected_version = "IV"
                            else:
                                auto_detected_version = "SA"
                        else:
                            # fallback: 文件名判断
                            txt_name = os.path.basename(self.gxt_txt_path).lower()
                            if "gta3" in txt_name:
                                auto_detected_version = "III"
                            elif "gtavc" in txt_name:
                                auto_detected_version = "VC"
                            elif "gtasa" in txt_name:
                                auto_detected_version = "SA"
                            elif "gta4" in txt_name:
                                auto_detected_version = "IV"
                            else:
                                auto_detected_version = "SA"
                except Exception:
                    auto_detected_version = "SA"

            # 弹窗让用户选择版本，所有文本迁移至lang文件
            version_map = {
                "III": self.tr("gta3_version"),
                "VC": self.tr("gtavc_version"),
                "SA": self.tr("gtasa_version"),
                "IV": self.tr("gtaiv_version"),
            }
            version_keys = ["III", "VC", "SA", "IV"]
            default_idx = version_keys.index(auto_detected_version) if auto_detected_version in version_keys else 2
            items = [f"{v}（{version_map[v]}）" for v in version_keys]
            msg = self.tr("auto_detected_version_msg", auto_detected_version=auto_detected_version)
            item, ok = QtWidgets.QInputDialog.getItem(self, self.tr("select_gxt_version_title"), msg, items, default_idx, False)
            if ok and item:
                version = version_keys[items.index(item)]
            else:
                return  # 用户取消

        output_txt_path = {
            'III': os.path.join(debug_dir, "gta3.txt"),
            'VC': os.path.join(debug_dir, "gtavc.txt"),
            'SA': os.path.join(debug_dir, "gtasa.txt"),
            'IV': os.path.join(debug_dir, "gta4.txt")
        }.get(str(version))

        if not output_txt_path:
            QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_unknown_gxt_version"))
            return

        with open(output_txt_path, 'w', encoding='utf-8') as output_file:
            for row in range(self.output_table.rowCount()):
                # 遍历表格的每一行
                key_item = self.output_table.item(row, 0)  # 获取第0列（key）的单元格
                value_item = self.output_table.item(row, 1)  # 获取第1列（value）的单元格
                if key_item and value_item:
                    # 如果key和value都存在
                    line = f"{key_item.text()}={value_item.text()}\n"  # 构造"key=value"格式的字符串并换行
                    if '[' in key_item.text():
                        # 如果key中包含'['，说明是section行，需要去掉等号
                        line = line.replace('=', '', 1)  # 只替换第一个等号
                    output_file.write(line)  # 写入到输出文件

        builder_exe = {
            'III': 'LCGXT.py',  # GTA3版本使用LCGXT.py
            'VC': 'VCGXT.py',   # GTAVC版本使用VCGXT.py
            'SA': 'SAGXT.py',   # GTASA版本使用SAGXT.py
            'IV': 'IVGXT.py'    # GTAIV版本使用IVGXT.py
        }.get(str(version))  # 根据版本选择对应的构建器

        if not builder_exe:
            # 如果没有找到对应的构建器，弹出错误提示
            QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_unknown_gxt_version"))
            return

        builder_path = os.path.join("builder", builder_exe)
        debug_builder_path = os.path.join(debug_dir, builder_exe)

        if not os.path.isfile(builder_path):
            QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_builder_exe_not_found", exe=builder_exe))
            return

        shutil.copy(builder_path, debug_builder_path)

        try:
            subprocess.run(["python", debug_builder_path, output_txt_path], check=True, cwd=debug_dir)
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_running_builder", error=str(e)))
            return

        gxt_files = [f for f in os.listdir(debug_dir) if f.endswith('.gxt')]
        if gxt_files:
            generated_gxt_path = os.path.join(debug_dir, gxt_files[0])
            # 保存到txt或gxt同目录
            if self.gxt_file_path:
                base_name = os.path.splitext(os.path.basename(self.gxt_file_path))[0]
                # 备份原始GXT文件
                backup_gxt_path = os.path.join(gxt_dir, f"{base_name}_backup.gxt")
                shutil.copy(self.gxt_file_path, backup_gxt_path)
                # 替换原始GXT文件
                shutil.copy(generated_gxt_path, self.gxt_file_path)
                QMessageBox.information(self, self.tr("prompt_messages"), self.tr("info_file_saved", path=self.gxt_file_path, backup_path=backup_gxt_path))
            else:
                base_name = os.path.splitext(os.path.basename(self.gxt_txt_path or ""))[0]
                edited_gxt_path = os.path.join(gxt_dir, f"{base_name}_Edited.gxt")
                shutil.copy(generated_gxt_path, edited_gxt_path)
                QMessageBox.information(self, self.tr("prompt_messages"), self.tr("info_gxt_saved", path=edited_gxt_path))
        else:
            QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_gxt_not_generated"))

    def add_row_buttons(self, row):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(10)

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
        base_size = 20
        add_btn = QPushButton("+")
        add_btn.setStyleSheet(btn_style.format(
            size=base_size,
            hover_color="#81C784",
            press_color="#4CAF50"
        ) + "background: #66BB6A; color: white;")
        del_btn = QPushButton("-")
        del_btn.setStyleSheet(btn_style.format(
            size=base_size,
            hover_color="#EF5350",
            press_color="#D32F2F"
        ) + "background: #EF9A9A; color: white;")

        layout.addWidget(add_btn)
        layout.addWidget(del_btn)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        try:
            add_btn.clicked.disconnect()
        except Exception:
            pass
        add_btn.clicked.connect(lambda: self.safe_add_row(row))
        try:
            del_btn.clicked.disconnect()
        except Exception:
            pass
        del_btn.clicked.connect(lambda: self.safe_delete_row(row))

        self.output_table.setCellWidget(row, 2, widget)

    def handle_add_button_clicked(self):
        sender = self.sender()
        if sender is not None:
            pw = sender.parent()
            if isinstance(pw, QWidget):  # 确保是 QWidget 实例
                row_position = self.output_table.indexAt(pw.pos()).row()
                self.safe_add_row(row_position)

    def handle_delete_button_clicked(self):
        sender = self.sender()
        if sender is not None:
            pw = sender.parent()
            if isinstance(pw, QWidget):  # 确保是 QWidget 实例
                row_position = self.output_table.indexAt(pw.pos()).row()
                self.safe_delete_row(row_position)

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

    def on_sidebar_button_clicked(self, section_name, row_section_map):
        """处理侧边栏按钮点击事件"""
        # 取消其他按钮的选中状态
        for button, name in self.section_buttons:
            if name != section_name:
                button.setChecked(False)
            else:
                button.setChecked(True)
        
        # 滚动到对应的表格行
        if section_name in row_section_map:
            row = row_section_map[section_name]
            self.output_table.scrollToItem(self.output_table.item(row, 0), QAbstractItemView.ScrollHint.PositionAtTop)
            # 高亮显示该行
            self.output_table.selectRow(row)

    def create_sidebar_buttons(self, section_names, row_section_map):
        """创建侧边栏按钮"""
        # 清除现有的侧边栏按钮
        for i in reversed(range(self.sidebar_layout.count())):
            item = self.sidebar_layout.itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
        
        # 清空按钮引用列表
        self.section_buttons = []
        
        # 为每个section创建按钮
        for section_name in section_names:
            button = QPushButton(section_name)
            button.setCheckable(True)
            button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px 12px;
                    border: none;
                    border-radius: 6px;
                    background: transparent;
                    color: #4A5568;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: #EBF8FF;
                }
                QPushButton:checked {
                    background: #4299E1;
                    color: white;
                }
            """)
            button.clicked.connect(lambda checked, name=section_name: self.on_sidebar_button_clicked(name, row_section_map))
            self.sidebar_layout.addWidget(button)
            self.section_buttons.append((button, section_name))

    def schedule_search(self, text):
        """调度搜索，使用防抖机制"""
        # 每次文本变化时重启定时器
        self.search_timer.stop()
        self.search_timer.start(300)  # 300毫秒防抖延迟

    def perform_search(self):
        """执行实际的搜索操作"""
        search_text = self.search_entry.text()
        self.filter_table(search_text)

    def toggle_regex_mode(self):
        """切换正则表达式模式"""
        self.regex_mode = self.regex_button.isChecked()
        if self.regex_mode:
            self.regex_button.setStyleSheet("""
                QPushButton {
                    background-color: #4299E1;
                    color: white;
                    border: 1px solid #4299E1;
                    border-radius: 6px;
                    font-weight: bold;
                    padding: 0px;
                }
            """)
        else:
            self.regex_button.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #CBD5E0;
                    border-radius: 6px;
                    font-weight: bold;
                    padding: 0px;
                }
                QPushButton:checked {
                    background-color: #4299E1;
                    color: white;
                    border: 1px solid #4299E1;
                }
            """)
        # 重新执行搜索以应用新模式
        self.schedule_search(self.search_entry.text())

    def filter_table(self, text):
        """优化的表格过滤功能"""
        # 如果搜索文本为空，显示所有行
        if not text:
            for row in range(self.output_table.rowCount()):
                self.output_table.setRowHidden(row, False)
            return

        # 正则表达式模式
        if self.regex_mode:
            try:
                pattern = re.compile(text, re.IGNORECASE)
                regex_valid = True
            except re.error:
                regex_valid = False
        
        # 检查缓存 - 为正则表达式模式和普通模式分别缓存
        cache_key = (text, self.regex_mode)
        if cache_key in self.search_cache:
            # 使用缓存的结果
            cached_result = self.search_cache[cache_key]
            for row, hidden in cached_result.items():
                self.output_table.setRowHidden(row, hidden)
            return

        # 构建表格数据缓存（如果尚未构建）
        if not self.table_data_cache or len(self.table_data_cache) != self.output_table.rowCount():
            self.table_data_cache = []
            for row in range(self.output_table.rowCount()):
                key_item = self.output_table.item(row, 0)
                value_item = self.output_table.item(row, 1)
                key_text = key_item.text() if key_item else ""
                value_text = value_item.text() if value_item else ""
                self.table_data_cache.append((key_text, value_text))

        # 执行搜索并逐个显示结果
        result_cache = {}
        
        if self.regex_mode and regex_valid:
            # 正则表达式搜索
            for row, (key_text, value_text) in enumerate(self.table_data_cache):
                try:
                    match = (pattern.search(key_text) is not None or 
                            pattern.search(value_text) is not None)
                except re.error:
                    match = False
                hidden = not match
                result_cache[row] = hidden
                self.output_table.setRowHidden(row, hidden)
                # 处理事件队列，使界面更新更流畅
                if row % 50 == 0:  # 每50行处理一次事件
                    QApplication.processEvents()
        elif self.regex_mode and not regex_valid:
            # 正则表达式无效，隐藏所有行
            for row in range(self.output_table.rowCount()):
                result_cache[row] = True
                self.output_table.setRowHidden(row, True)
                # 处理事件队列，使界面更新更流畅
                if row % 50 == 0:  # 每50行处理一次事件
                    QApplication.processEvents()
        else:
            # 普通文本搜索
            text_lower = text.lower()
            for row, (key_text, value_text) in enumerate(self.table_data_cache):
                key_text_lower = key_text.lower()
                value_text_lower = value_text.lower()
                match = text_lower in key_text_lower or text_lower in value_text_lower
                hidden = not match
                result_cache[row] = hidden
                self.output_table.setRowHidden(row, hidden)
                # 处理事件队列，使界面更新更流畅
                if row % 50 == 0:  # 每50行处理一次事件
                    QApplication.processEvents()

        # 更新缓存（限制缓存大小）
        if len(self.search_cache) > 50:  # 限制缓存大小为50个搜索词
            self.search_cache.clear()
        self.search_cache[cache_key] = result_cache

    def safe_add_row(self, row):
        """安全地在指定行后插入一行（用于表格按钮）"""
        self.output_table.insertRow(row + 1)
        for col in range(self.output_table.columnCount()):
            self.output_table.setItem(row + 1, col, QTableWidgetItem(""))

    def safe_delete_row(self, row):
        """安全地删除指定行（用于表格按钮）"""
        if 0 <= row < self.output_table.rowCount():
            self.output_table.removeRow(row)

    def display_gxt_content_in_table(self, content: str):
        """
        将GXT或TXT内容字符串渲染到表格中。
        支持section和key=value格式，自动分配到表格行。
        """
        # 极致性能优化+按钮显示修复+选中可读性
        self.parsed_content = content
        self.output_table.setUpdatesEnabled(False)
        self.output_table.blockSignals(True)
        self.output_table.clearContents()

        # 清空搜索缓存，因为表格内容已更改
        self.search_cache.clear()
        self.table_data_cache = []

        # 清空搜索缓存，当表格内容更改时同时清除正则模式下的缓存
        self.regex_mode = False
        self.regex_button.setChecked(False)
        self.regex_button.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #4299E1;
                color: white;
            }
        """)

        # 预处理所有行，避免多次split和判断
        lines = content.split('\n')
        valid_lines = []
        section_names = []
        row_section_map = {}
        table_row = 0
        font_normal = QFont()
        font_bold = QFont()
        font_bold.setBold(True)

        append_valid = valid_lines.append
        append_section = section_names.append

        # 一次性遍历并分类
        for idx, line in enumerate(lines):
            if not line:
                continue
            if line.startswith('[') and line.endswith(']'):
                append_valid(('section', line))
            elif '=' in line:
                append_valid(('kv', line))

        row_count = len(valid_lines)
        self.output_table.setRowCount(row_count)


        # 用 setItem 代替 __setitem__，避免类型错误
        for idx, (typ, line) in enumerate(valid_lines):
            if typ == 'section':
                section = line[1:-1]
                append_section(section)
                row_section_map[section] = idx
                item = QTableWidgetItem(line)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                item.setFont(font_bold)
                self.output_table.setItem(idx, 0, item)
                self.output_table.setItem(idx, 1, QTableWidgetItem(""))
            elif typ == 'kv':
                eq = line.find('=')
                key = line[:eq].strip()
                value = line[eq+1:].strip()
                key_item = QTableWidgetItem(key)
                value_item = QTableWidgetItem(value)
                key_item.setFont(font_normal)
                value_item.setFont(font_bold)  # 将内容列设置为粗体
                self.output_table.setItem(idx, 0, key_item)
                self.output_table.setItem(idx, 1, value_item)

        self.output_table.setRowCount(row_count)

        # 设置行号
        for i in range(row_count):
            self.output_table.setVerticalHeaderItem(i, QTableWidgetItem(str(i + 1)))

        # 创建侧边栏按钮
        self.create_sidebar_buttons(section_names, row_section_map)

        self.output_table.blockSignals(False)
        self.output_table.setUpdatesEnabled(True)
        viewport = self.output_table.viewport()
        if viewport is not None:
            viewport.update()

        # --- 优化：鼠标悬停显示按钮 ---
        for r in range(self.output_table.rowCount()):
            self.output_table.removeCellWidget(r, 2)

        def get_btn_widget(row):
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(2, 0, 2, 0)
            layout.setSpacing(10)
            add_btn = QPushButton("+")
            del_btn = QPushButton("-")
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
            base_size = 20
            add_btn.setStyleSheet(btn_style.format(
                size=base_size,
                hover_color="#81C784",
                press_color="#4CAF50"
            ) + "background: #66BB6A; color: white;")
            del_btn.setStyleSheet(btn_style.format(
                size=base_size,
                hover_color="#EF5350",
                press_color="#D32F2F"
            ) + "background: #EF9A9A; color: white;")
            layout.addWidget(add_btn)
            layout.addWidget(del_btn)
            try:
                add_btn.clicked.disconnect()
            except Exception:
                pass
            add_btn.clicked.connect(lambda: self.safe_add_row(row))
            try:
                del_btn.clicked.disconnect()
            except Exception:
                pass
            del_btn.clicked.connect(lambda: self.safe_delete_row(row))
            widget.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            return widget

        class TableHoverEventFilter(QtCore.QObject):
            def __init__(self, table, btn_widget_pool, get_btn_widget):
                super().__init__(table)
                self.table = table
                self.get_btn_widget = get_btn_widget
                self.last_row = -1

            def eventFilter(self, obj, event):
                if event.type() == QtCore.QEvent.Type.MouseMove:
                    pos = event.pos()
                    index = self.table.indexAt(pos)
                    row = index.row()
                    if row != self.last_row:
                        if 0 <= self.last_row < self.table.rowCount():
                            self.table.removeCellWidget(self.last_row, 2)
                        self.last_row = row
                        if 0 <= row < self.table.rowCount():
                            item = self.table.item(row, 0)
                            if item and not (item.text().startswith('[') and item.text().endswith(']')):
                                self.table.setCellWidget(row, 2, self.get_btn_widget(row))
                            else:
                                self.table.removeCellWidget(row, 2)
                    return False
                elif event.type() == QtCore.QEvent.Type.Leave:
                    if 0 <= self.last_row < self.table.rowCount():
                        self.table.removeCellWidget(self.last_row, 2)
                    self.last_row = -1
                    return False
                return super().eventFilter(obj, event)

        viewport = self.output_table.viewport()
        if hasattr(self, "_table_hover_filter") and self._table_hover_filter and viewport is not None:
            viewport.removeEventFilter(self._table_hover_filter)
        self._table_hover_filter = TableHoverEventFilter(self.output_table, None, get_btn_widget)
        if viewport is not None:
            viewport.installEventFilter(self._table_hover_filter)
        self.output_table.setMouseTracking(True)
        # --- 结束 ---

        # 移除对section_combobox的引用，因为我们现在使用侧边栏导航
        # self.section_combobox.currentIndexChanged.connect(
        #     lambda idx: self.scroll_to_section(idx, row_section_map)
        # )

    def smart_translate_table(self):
        """智能翻译当前表格内容，带进度反馈，完全异步，主线程不阻塞"""
        # 计算实际可翻译行数（排除章节标记行）
        translatable_rows = 0
        for row in range(self.output_table.rowCount()):
            key_item = self.output_table.item(row, 0)
            if key_item and not (key_item.text().startswith('[') and key_item.text().endswith(']')):
                translatable_rows += 1

        if translatable_rows == 0:
            QMessageBox.information(self, self.tr("info_title"), self.tr("info_no_translatable_content"))
            return

        # 检查用户是否输入了KEY
        key, ok = QtWidgets.QInputDialog.getText(self, self.tr("input_key_title"), self.tr("input_key_prompt"))
        if not ok or not key:
            QMessageBox.warning(self, self.tr("warning_title"), self.tr("warning_input_valid_key"))
            return

        dlg = TranslationProgressDialog(translatable_rows, self)
        dlg.set_progress(0, self.tr("translate_preparing", translatable_rows=translatable_rows))
        dlg.show()
        QApplication.processEvents()

        worker = TranslationWorker(self, key)
        
        def on_progress(current, total, msg):
            # 直接使用终端输出的原始进度数据
            dlg.set_progress(current, msg)
            QtCore.QCoreApplication.processEvents()
            
        def on_finished():
            # 仅当终端输出显示完成时才更新进度
            if dlg.progress.value() == translatable_rows:
                dlg.set_progress(translatable_rows, self.tr("translate_complete"))
                self.update_parsed_content_from_table()
                QtCore.QTimer.singleShot(800, dlg.accept)
            else:
                # 如果进度未完成，等待终端输出更新
                QtCore.QTimer.singleShot(500, on_finished)
            
        def on_error(msg):
            # 保持当前进度状态，仅更新错误信息
            dlg.set_progress(dlg.progress.value(), self.tr("translate_interrupted", msg=msg))
            QtCore.QTimer.singleShot(1200, dlg.accept)
            
        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)

        def on_cancel():
            worker.cancel()
        try:
            dlg.cancel_btn.clicked.disconnect()
        except Exception:
            pass
        dlg.cancel_btn.clicked.connect(on_cancel)
        dlg.cancel_btn.clicked.connect(dlg.reject)

        worker.start()

    def update_parsed_content_from_table(self):
        """从表格内容更新 parsed_content 变量"""
        content_lines = []
        current_section = ""
        
        for row in range(self.output_table.rowCount()):
            key_item = self.output_table.item(row, 0)
            value_item = self.output_table.item(row, 1)
            
            if key_item and value_item:
                key = key_item.text()
                value = value_item.text()
                
                if key.startswith('[') and key.endswith(']'):
                    current_section = key
                    content_lines.append(key)
                else:
                    content_lines.append(f"{key}={value}")
        
        self.parsed_content = "\n".join(content_lines)

    def closeEvent(self, event):
        """覆盖关闭事件，确保程序完全退出"""
        QApplication.quit()

class TranslationWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, main_window, key=None):
        super().__init__()
        self.main_window = main_window
        self.key = key
        self._cancelled = False

    def run(self):
        try:
            import logging
            logger = logging.getLogger("Translator")
            logger.info("TranslationWorker开始运行")
            
            from master.smart_translate import smart_translate
            def progress_callback(current, total, msg=""):
                logger.info(f"进度更新: {current}/{total} - {msg}")
                self.progress.emit(current, total, msg)
                if self._cancelled:
                    logger.warning("翻译任务被取消")
                    raise Exception(self.main_window.tr("translation_cancelled"))
            
            # 验证KEY
            logger.info("验证API密钥")
            if not self.key or len(self.key) < 8:
                logger.error("API密钥无效")
                raise Exception(self.main_window.tr("invalid_key_error"))
            
            # 记录日志
            logger.info("记录翻译开始日志")
            self.progress.emit(0, 100, self.main_window.tr("translation_start_log", api_key=self.key))
            logger.info("调用smart_translate函数")
            smart_translate(self.main_window, progress_callback=progress_callback, key=self.key)
            logger.info("翻译任务完成")
            self.finished.emit()
        except Exception as e:
            import logging
            logger = logging.getLogger("Translator")
            logger.error(f"TranslationWorker发生异常: {e}")
            self.error.emit(str(e))

    def cancel(self):
        self._cancelled = True

class TranslationProgressDialog(QDialog):
    def __init__(self, total, parent=None):
        super().__init__(parent)
        self._tr_func = parent.tr if parent and hasattr(parent, 'tr') else lambda key, **kwargs: key
        self.setWindowTitle(self._tr_func("smart_translate_progress"))
        self.setModal(True)
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)
        
        # 进度条和标签
        self.label = QLabel(self._tr_func("translate_preparing_progress"), self)
        self.progress = QtWidgets.QProgressBar(self)
        self.progress.setRange(0, total)
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        
        # 日志显示区域
        self.log_area = QTextEdit(self)
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("font-family: Consolas, 'Courier New', monospace; font-size: 12px;")
        layout.addWidget(self.log_area)
        
        # 取消按钮
        self.cancel_btn = QPushButton(self._tr_func("cancel_button_text"), self)
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        
        self._cancelled = False

    def set_progress(self, value, text=None):
        self.progress.setValue(value)
        if text:
            self.label.setText(text)
            self.log_area.append(text)  # 将日志信息添加到日志区域
        QApplication.processEvents()

    def cancelled(self):
        return self._cancelled or self.result() == QDialog.DialogCode.Rejected

    def reject(self):
        import logging
        logger = logging.getLogger("Translator")
        logger.info("用户点击取消按钮")
        self._cancelled = True
        super().reject()

def main():
    def excepthook(exc_type, exc_value, exc_tb):
        import traceback
        msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        show_copyable_error(None, "未捕获异常", msg)
        sys.exit(1)

    sys.excepthook = excepthook
    
    app = QApplication([])

    app.setApplicationVersion(APP_VERSION)

    app.setStyleSheet("""
        /* ========== 基础框架样式 ========== 
        设计目标：建立统一的视觉基线和呼吸感 */
        QWidget {
            background: #F8FAFC;  /* 主背景色-浅灰 */
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
            qproperty-alignment: 'AlignCenter'; /* 居中显示 */
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
        /* 修正选中单元格文字颜色为黑色 */
        QTableWidget::item:selected {
            color: #222 !important;
            background: #BEE3F8;
        }
        /* 编辑框半透明+模糊效果 */
        QTableWidget QLineEdit {
            background: rgba(255,255,255,0.7);
            border: 2px solid #63B3ED;
            border-radius: 8px;
            padding: 8px;
            color: #222;

        }
        QTableWidget QLineEdit:focus {
            background: rgba(255,255,255,0.85);
            border: 2px solid #3182CE;
            color: #111;
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
            background: #F1F5F9;
            width: 12px;
            margin: 2px 0 2px 0;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background: #BFD7ED;
            min-height: 40px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical:hover {
            background: #7BA7D7;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            background: none;
            border: none;
            height: 0px;
        }
        QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
            width: 0; height: 0;
            background: none;
        }
        QScrollBar:horizontal {
            background: #F1F5F9;
            height: 12px;
            margin: 0 2px 0 2px;
            border-radius: 6px;
        }
        QScrollBar::handle:horizontal {
            background: #BFD7ED;
            min-width: 40px;
            border-radius: 6px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #7BA7D7;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            background: none;
            border: none;
            width: 0px;
        }
        QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
            width: 0; height: 0;
            background: none;
        }
        /* ========== 操作按钮 ==========
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
    # 使主窗口获得焦点以便快捷键生效
    window.setFocus()

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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply == QMessageBox.StandardButton.Yes:
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
        window.open_gxt_file(gxt_path)

    app.exec()

if __name__ == '__main__':
    main()