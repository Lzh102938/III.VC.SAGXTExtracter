import os
import errno
import gta.gxt
import ctypes
from PyQt6 import QtWidgets, QtGui, QtCore
from builder.IVGXT import *
from builder.LCGXT import *
from builder.SAGXT import *
from builder.VCGXT import *
from PyQt6.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGroupBox, QFileDialog,
    QMessageBox, QTableWidget, QTableWidgetItem, QLineEdit, QWidget, QComboBox, QAbstractItemView, QDialog, QHeaderView, QSizePolicy,
    QStyledItemDelegate, QMenu, QTextEdit, QFontDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint, QRect
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
from Debug_menu.debug_menu import DebugMenu

# Windows API相关导入
try:
    import win32gui
    import win32con
    import win32api
    from ctypes import windll
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False


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
    edit.setStyleSheet("font-family: Consolas, 'Courier New', monospace; font-size: 13px; background: transparent;")
    layout.addWidget(edit)
    btn = QPushButton("关闭")
    btn.clicked.connect(dlg.accept)
    btn.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { background: rgba(0, 0, 0, 0.1); } QPushButton:pressed { background: rgba(0, 0, 0, 0.2); }")
    layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight)
    dlg.setModal(True)
    dlg.exec()

APP_VERSION = "2.4.0"
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
        self._last_text = text  # 添加文本历史记录属性

class TableItemHistoryManager:
    """表格项修改历史管理器"""
    def __init__(self):
        self._item_history = {}  # 存储表格项的修改历史
        
    def set_last_text(self, item, text):
        """设置表格项的上次文本"""
        item_id = id(item)
        self._item_history[item_id] = text
        
    def get_last_text(self, item):
        """获取表格项的上次文本"""
        item_id = id(item)
        return self._item_history.get(item_id, "")

class GXTViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.gxt_file_path = None
        self.gxt_txt_path = None
        self.parsed_content = ""
        self.translations = {}
        self._current_language = '简体中文.lang'  # 添加当前语言属性
        self._row_cache = None  # 新增：缓存表格行数据
        self.debug_menu = DebugMenu(self)
        self._table_hover_filter = None  # 防止未定义
        self.section_buttons = []  # 初始化section_buttons属性
        self.regex_mode = False  # 添加正则表达式模式标志
        self._char_tooltip_filter = None  # 添加字符提示过滤器
        self.char_tooltip = QtWidgets.QToolTip  # 添加工具提示对象
        self.background_pixmap = None  # 添加背景图片属性
        self._blur_radius_value = 0  # 添加背景模糊半径属性
        self._brightness_value = 0  # 添加背景亮度属性
        self.value_column_font = QFont()  # 添加Value列字体属性
        self.value_column_font.setBold(True)  # 默认粗体
        self.mounted_table = None  # 添加挂载的码表属性
        self.table_conversion_state = 'original'  # 添加码表转换状态属性
        self.table_item_history = TableItemHistoryManager()  # 添加表格项历史管理器
        
        self.load_language_file()
        self.initUI()
        self.installEventFilter(self)  # 用于全局快捷键
        self.load_background_settings()  # 加载背景设置
        self.load_font_settings()  # 加载字体设置



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
        


        
        # 创建状态栏，用于显示版本和解析时间
        self.status_bar = QWidget()
        self.status_bar_layout = QHBoxLayout(self.status_bar)
        self.status_bar_layout.setContentsMargins(0, 0, 0, 0)
        self.status_bar_layout.setSpacing(10)
        
        # 添加版本图标标签
        self.version_icon_label = QLabel()
        self.version_icon_label.setFixedSize(16, 16)
        self.version_icon_label.setMinimumSize(16, 16)
        self.version_icon_label.setMaximumSize(16, 16)
        self.version_icon_label.setScaledContents(False)  # 改为False，手动控制缩放
        self.version_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.version_icon_label.setStyleSheet("QLabel { margin: 0px 0px 0px 0px; padding: 0px; border: none; background: transparent; vertical-align: middle; }")
        self.version_icon_label.setVisible(False)  # 初始隐藏
        
        # 版本和解析时间标签
        self.version_label = QLabel(f"{self.tr('title_version')} -")
        self.version_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        self.elapsed_label = QLabel("")
        self.elapsed_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        
        # 添加版本号标签
        self.app_version_label = QLabel(f"版本: {APP_VERSION}")
        self.app_version_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        
        # 添加时间戳标签
        self.timestamp_label = QLabel("")
        self.timestamp_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        
        # 添加状态消息标签
        self.status_message_label = QLabel("")
        self.status_message_label.setObjectName("status_message")
        self.status_message_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        
        self.status_bar_layout.addWidget(self.version_icon_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.status_bar_layout.addWidget(self.version_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.status_bar_layout.addWidget(self.elapsed_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.status_bar_layout.addWidget(self.app_version_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.status_bar_layout.addWidget(self.timestamp_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.status_bar_layout.addWidget(self.status_message_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.status_bar_layout.addStretch()
        
        # 设置状态栏样式
        self.status_bar.setStyleSheet("""
            QWidget {
                background: transparent;
                border-top: 1px solid #E2E8F0;
                padding: 7px 0 4px 0;
                margin-top: 5px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)
        
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



        # 创建左侧边栏
        side_bar_layout = QVBoxLayout()
        side_bar_layout.setContentsMargins(0, 0, 0, 0)
        side_bar_layout.setSpacing(10)
        
        # 左侧边栏内容区
        self.side_bar_content = QWidget()
        self.side_bar_content.setStyleSheet("background: transparent; border: none;")
        side_bar_layout.addWidget(self.side_bar_content)
        
        # 主布局
        main_horizontal_layout = QHBoxLayout()
        main_horizontal_layout.addLayout(side_bar_layout, 1)
        
        control_layout = QVBoxLayout()

        self.gxt_path_entry = QLineEdit(self)
        self.gxt_path_entry.setVisible(False)
        #control_layout.addWidget(self.gxt_path_entry)

        # 简化标题区域
        self.title_label = ClickableLabel(self.tr("window_title"))
        self.title_label.setOpenExternalLinks(True)
        self.title_label.setToolTip(self.tr("tooltip_title"))
        self.title_label.clicked.connect(self.open_about_window)
        self.title_label.setStyleSheet("""
            ClickableLabel { 
                color: #2c2c2c; 
                font-size: 28px; 
                font-weight: bold; 
                padding: 5px 0;
                background: transparent;
            }
        """)
        main_layout.addWidget(self.title_label)

        button_groupbox = QGroupBox(self.tr("change_the_row"))
        button_layout = QHBoxLayout()
        button_container = QWidget()
        button_container.setObjectName("button_container")
        button_layout = QHBoxLayout(button_container)

        self.browse_button = QPushButton(self.tr("browse_button_text"), self)
        self.browse_button.clicked.connect(self.select_gxt_file)
        self.browse_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 12px; padding: 5px; min-width: 100px; min-height: 28px; font-size: 14px; font-weight: bold; background: rgba(66, 153, 225, 0.8); }")
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(2)
        shadow.setOffset(1, 1)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.browse_button.setGraphicsEffect(shadow)
        self.browse_button.setToolTip(self.tr("tooltip_browse_button"))
        button_layout.addWidget(self.browse_button)

        self.convert_button = QPushButton(self.tr("convert_button_text"), self)
        self.convert_button.clicked.connect(self.convert_using_table)
        self.convert_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 12px; padding: 5px; min-width: 100px; min-height: 28px; font-size: 14px; font-weight: bold; background: rgba(66, 153, 225, 0.8); }")
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(2)
        shadow.setOffset(1, 1)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.convert_button.setGraphicsEffect(shadow)
        self.convert_button.setToolTip(self.tr("tooltip_convert_button"))
        button_layout.addWidget(self.convert_button)

        self.save_button = QPushButton(self.tr("save_button_text"), self)
        self.save_button.clicked.connect(self.save_generated_txt)
        self.save_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 12px; padding: 5px; min-width: 100px; min-height: 28px; font-size: 14px; font-weight: bold; background: rgba(66, 153, 225, 0.8); }")
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
        self.clear_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 12px; padding: 5px; min-width: 100px; min-height: 28px; font-size: 14px; font-weight: bold; background: rgba(66, 153, 225, 0.8); }")
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(2)
        shadow.setOffset(1, 1)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.clear_button.setGraphicsEffect(shadow)
        self.clear_button.setToolTip(self.tr("tooltip_clear_button"))
        button_layout.addWidget(self.clear_button)

        self.save_gxt_button = QPushButton(self.tr("save_gxt_button_text"), self)
        self.save_gxt_button.clicked.connect(self.save_and_build_gxt)
        self.save_gxt_button.setStyleSheet("QPushButton { border: 2px solid gray; border-radius: 12px; padding: 5px; min-width: 100px; min-height: 28px; font-size: 14px; font-weight: bold; background: rgba(66, 153, 225, 0.8); }")
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
                border: 2px solid rgba(241, 245, 249, 0.5);
                border-radius: 12px;
                margin-top: 16px;
                padding-top: 10px;
                background: rgba(241, 245, 249, 0.3); /* 调整背景颜色为半透明浅灰色 */
                min-width: 180px;
                max-width: 250px;
                height: 100%;
            }
            QGroupBox::title {
                color: #4A5568;
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 3px;
                background: transparent;
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
        viewport = self.sidebar_scroll.viewport()
        if viewport is not None:
            viewport.setStyleSheet("background: transparent;")
        self.sidebar.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.sidebar_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
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

        self.output_table = QTableWidget(self)
        self.output_table.setUpdatesEnabled(False)
        self.output_table.setViewportMargins(0, 0, 0, 0)
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
                    background: transparent;  /* 改为透明背景 */
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
        
        # 创建提示标签
        self.placeholder_label = QLabel(self)
        self.placeholder_label.setText(f'''<div style="text-align: center;">
<h2 style="color: #6B7280; margin-bottom: 10px;">永远相信美好的事情即将发生</h2>
<p style="color: #9CA3AF; font-size: 14px;">将GXT、TXT拖入这里吧</p>
<p style="color: #3B82F6; font-size: 14px; text-decoration: underline; cursor: pointer;" id="new_start_link">新的开始</p>
</div>''')
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("background: transparent; border-radius: 12px; border: 1px solid rgba(226, 232, 240, 0.7);")
        # 设置提示标签的尺寸策略，使其可以扩展填充空间
        self.placeholder_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # 启用鼠标跟踪并设置光标形状
        self.placeholder_label.setMouseTracking(True)
        self.placeholder_label.setCursor(Qt.CursorShape.PointingHandCursor)
        # 连接点击信号到选择GXT文件的槽函数
        self.placeholder_label.mousePressEvent = self._on_placeholder_clicked
        
        # 将表格和提示标签添加到右侧内容布局
        right_content_layout.addWidget(self.output_table)
        right_content_layout.addWidget(self.placeholder_label)

        # 获取表格的头部并设置列宽
        header = self.output_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, SectionResizeMode.Fixed)
            header.setSectionResizeMode(1, SectionResizeMode.Stretch)
            header.setSectionResizeMode(2, SectionResizeMode.Fixed)
            # 设置固定宽度
            self.output_table.setColumnWidth(0, 100)  # 第一列宽度固定，适合8个字符
            self.output_table.setColumnWidth(2, 80)  # 第三列宽度固定，适合按钮

        # 初始化时隐藏表格并显示占位符
        self.output_table.setVisible(False)
        self.placeholder_label.setVisible(True)
        
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
                background-color: rgba(240, 240, 240, 0.7);
                border: 1px solid rgba(203, 213, 224, 0.7);
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                padding: 0px;
                min-width: 32px;
                max-width: 32px;
                min-height: 32px;
                max-height: 32px;
            }
            QPushButton:checked {
                background-color: rgba(66, 153, 225, 0.8);
                color: white;
                border: 1px solid rgba(66, 153, 225, 0.8);
            }
        """)
        self.regex_button.clicked.connect(self.toggle_regex_mode)
        
        # 添加事件过滤器以确保按钮尺寸不会改变
        self.regex_button.installEventFilter(self)
        
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
        
        # 添加状态栏到主布局
        main_layout.addWidget(self.status_bar)

        self.setLayout(main_layout)
        self.setAcceptDrops(True)
        self.create_context_menu()  # 创建右键菜单

        lineedit_style = """
            QLineEdit {
                background: rgba(255,255,255,0.5);
                border: 1px solid #CBD5E0;
                border-radius: 6px;
                padding: 4px 8px;  /* 减少垂直内边距以适应32px高度 */
                selection-background-color: #90CDF4;
            }
            QLineEdit:focus {
                border: 2px solid #63B3ED;
                background: rgba(255,255,255,0.7);
            }
        """
        
        # 应用样式到所有输入框
        self.search_entry.setStyleSheet(lineedit_style)
        self.gxt_path_entry.setStyleSheet(lineedit_style)

        # 安装事件过滤器
        self.search_entry.installEventFilter(self)
        self.gxt_path_entry.installEventFilter(self)

    def create_context_menu(self):
        """创建右键上下文菜单"""
        self.context_menu = QMenu(self)
        
        # 更改语言选项
        language_menu = self.context_menu.addMenu(self.tr("change_language_text"))
        
        # 添加所有可用语言作为子菜单项
        if language_menu is not None:
            for lang in self.available_languages:
                action = language_menu.addAction(lang)
                if action is not None:
                    action.triggered.connect(lambda checked, l=lang: self.change_language_by_action(l))
        
        # 设置背景选项
        set_background_action = QAction(self.tr("set_background_text"), self)
        set_background_action.triggered.connect(self.show_background_settings)
        if self.context_menu is not None:
            self.context_menu.addAction(set_background_action)
        
        # 字体设置选项
        font_settings_action = QAction(self.tr("set_value_font"), self)
        font_settings_action.triggered.connect(self.show_font_settings)
        if self.context_menu is not None:
            self.context_menu.addAction(font_settings_action)
        
        # 码表操作选项
        # 始终添加挂载码表选项（始终打开选择窗口）
        load_table_action = QAction(self.tr("table_mount"), self)
        load_table_action.triggered.connect(self.mount_table_via_menu)
        if self.context_menu is not None:
            self.context_menu.addAction(load_table_action)
            
        # 始终添加卸载码表选项
        unload_table_action = QAction(self.tr("table_unmount"), self)
        unload_table_action.triggered.connect(self.unload_conversion_table)
        if self.context_menu is not None:
            self.context_menu.addAction(unload_table_action)
        
        # 添加分隔线
        if self.context_menu is not None:
            self.context_menu.addSeparator()
            
        # 添加Debug菜单选项
        debug_menu_action = QAction(self.tr("open_debug_menu"), self)
        debug_menu_action.triggered.connect(lambda: self.debug_menu.show_menu() if self.debug_menu else None)
        if self.context_menu is not None:
            self.context_menu.addAction(debug_menu_action)
            
        # 添加分隔线
        if self.context_menu is not None:
            self.context_menu.addSeparator()
        
        # 关于选项
        about_action = QAction(self.tr("about_action_text"), self)
        about_action.triggered.connect(self.open_about_window)
        if self.context_menu is not None:
            self.context_menu.addAction(about_action)

    def unload_conversion_table(self):
        """卸载码表"""
        if self.mounted_table is None:
            self.status_message_label.setText("当前未挂载码表")
            return
            
        self.mounted_table = None
        self.table_conversion_state = 'original'
        self.status_message_label.setText("已卸载码表")
        # 重新创建上下文菜单以更新选项
        self.create_context_menu()

    def mount_table_via_menu(self):
        """通过右键菜单挂载码表 - 始终打开选择窗口"""
        from master.convert_using_table import mount_conversion_table
        try:
            from master.github_resources import GitHubResourceDialog
            github_dialog = GitHubResourceDialog(self)
            if github_dialog.exec() == QDialog.DialogCode.Accepted:
                resource = github_dialog.get_selected_resource()
                if resource == "local":
                    # 用户选择本地文件
                    file_path, _ = QFileDialog.getOpenFileName(self, self.tr("select_conversion_table"), "", "文本文件 (*.txt)")
                    if not file_path:
                        return
                    mount_conversion_table(self, file_path)
                elif resource and isinstance(resource, dict):
                    # 用户选择GitHub资源
                    try:
                        import requests
                        import tempfile
                        # 下载文件到临时文件
                        response = requests.get(resource['path'])
                        response.raise_for_status()
                        
                        # 创建临时文件
                        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8', suffix='.txt')
                        temp_file.write(response.text)
                        temp_file.close()
                        file_path = temp_file.name
                        
                        mount_conversion_table(self, file_path)
                        
                        # 清理临时文件
                        try:
                            os.unlink(temp_file.name)
                        except:
                            pass
                    except Exception as e:
                        QMessageBox.critical(self, self.tr("错误"), self.tr("从GitHub获取文件时出错: ") + str(e))
                else:
                    return  # 用户取消操作
            else:
                return  # 用户取消操作
        except ImportError as e:
            QMessageBox.critical(self, self.tr("错误"), self.tr("无法导入GitHub资源模块: ") + str(e))
            return

    def change_language_by_action(self, language):
        """通过右键菜单更改语言"""
        self._current_language = language  # 保存当前语言设置
        lang_file_path = os.path.join('languages', language)
        self.load_language_file(lang_file_path)
        self.update_ui_texts()

    def contextMenuEvent(self, event):
        """处理上下文菜单事件"""
        if hasattr(self, 'context_menu') and self.context_menu:
            self.context_menu.exec(event.globalPos())

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
        # 重新加载当前语言（通过右键菜单选择的语言）
        current_lang = '简体中文.lang'  # 默认语言
        if hasattr(self, '_current_language'):
            current_lang = self._current_language
        lang_file_path = os.path.join('languages', current_lang)
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
        # 通过右键菜单选择语言，此方法不再使用
        pass

    def update_ui_texts(self):
        self.setWindowTitle(self.tr("window_title"))
        self.title_label.setText(self.tr("window_title"))
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
            # 记录解析开始时的 Unix 时间戳
            timestamp = int(time.time())
            self.timestamp_label.setText(f"{timestamp}")
            
            with open(file_path, 'rb') as gxt:
                gxtversion = gta.gxt.getVersion(gxt)
                if not gxtversion:
                    self.version_icon_label.setVisible(False)
                    QMessageBox.critical(self, self.tr("error"), self.tr("error_unknown_gxt_version"))
                    return ""
                # 更新状态栏中的版本信息和图标
                self.version_label.setText(f"{self.tr('title_version')} {gxtversion}")
                self.update_version_icon(gxtversion)
                # 保持窗口标题不变
                self.setWindowTitle(self.tr("window_title"))

                gxtReader = gta.gxt.getReader(gxtversion)
                if gxtReader is None:
                    self.version_icon_label.setVisible(False)
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
                # 更新状态栏中的版本和解析时间信息
                self.version_label.setText(f"{self.tr('title_version')} {gxtversion}")
                self.update_version_icon(gxtversion)
                self.elapsed_label.setText(f"{elapsed:.3f}s")
                # 保留原有的窗口标题设置
                self.setWindowTitle(self.tr("window_title"))
                return content_str
        except Exception as e:
            self.version_icon_label.setVisible(False)
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
                # 显示表格并隐藏占位符
                self.output_table.setVisible(True)
                self.placeholder_label.setVisible(False)
                self.display_gxt_content_in_table(content)
            except Exception as e:
                QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_opening_gxt_file", error=str(e)))
        else:
            QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_invalid_gxt_file_path"))

    def _on_placeholder_clicked(self, ev):
        """处理提示标签点击事件，创建新表"""
        if ev.button() == Qt.MouseButton.LeftButton:
            # 创建预定义的文本内容
            content = "[新建表]\n新建键=新建值"
            # 复用导入txt的逻辑
            self.output_table.setVisible(True)
            self.placeholder_label.setVisible(False)
            self.display_gxt_content_in_table(content)
            # 设置默认路径，以便保存功能可以正常工作
            self.gxt_file_path = None
            script_dir = os.path.dirname(os.path.realpath(__file__))
            self.gxt_txt_path = os.path.join(script_dir, "new_table.txt")

    def select_gxt_file(self):
        """选择GXT文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("select_gxt_file"),
            "",
            "GXT文件 (*.gxt);;TXT文件 (*.txt);;所有文件 (*)"
        )
        if file_path:
            if file_path.lower().endswith('.gxt'):
                self.open_gxt_file(file_path)
            elif file_path.lower().endswith('.txt'):
                self.open_txt_file(file_path)

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
        # 清空时隐藏版本图标并重置版本信息
        self.version_icon_label.setVisible(False)
        self.version_label.setText(f"{self.tr('title_version')} -")
        self.elapsed_label.setText("")
        self.timestamp_label.setText("")

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
                # 更新版本信息和图标
                self.version_label.setText(f"{self.tr('title_version')} {version}")
                self.update_version_icon(version)
            else:
                return  # 用户取消

        output_txt_path = {
            'III': os.path.join(debug_dir, "gta3.txt"),
            'VC': os.path.join(debug_dir, "gtavc.txt"),
            'SA': os.path.join(debug_dir, "gtasa.txt"),
            'IV': os.path.join(debug_dir, "gta4.txt")
        }.get(str(version))

        if not output_txt_path:
            self.version_icon_label.setVisible(False)
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
            self.version_icon_label.setVisible(False)
            QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_unknown_gxt_version"))
            return

        # 根据版本选择对应的模块
        if version == "III":
            from builder.LCGXT import LCGXT
            generator = LCGXT()
            if not generator.load_text(output_txt_path):
                QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_loading_text"))
                return
            # 直接生成最终GXT文件
            if self.gxt_file_path:
                base_name = os.path.splitext(os.path.basename(self.gxt_file_path))[0]
                final_gxt_path = os.path.join(gxt_dir, f"{base_name}.gxt")
            else:
                base_name = os.path.splitext(os.path.basename(self.gxt_txt_path or ""))[0]
                final_gxt_path = os.path.join(gxt_dir, f"{base_name}.gxt")
            generator.save_as_gxt(final_gxt_path)
            generated_gxt_path = final_gxt_path
        elif version == "VC":
            from builder.VCGXT import VCGXT
            generator = VCGXT()
            if not generator.LoadText(output_txt_path):
                QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_loading_text"))
                return
            # 直接生成最终GXT文件
            if self.gxt_file_path:
                base_name = os.path.splitext(os.path.basename(self.gxt_file_path))[0]
                final_gxt_path = os.path.join(gxt_dir, f"{base_name}.gxt")
            else:
                base_name = os.path.splitext(os.path.basename(self.gxt_txt_path or ""))[0]
                final_gxt_path = os.path.join(gxt_dir, f"{base_name}.gxt")
            generator.SaveAsGXT(final_gxt_path)
            generated_gxt_path = final_gxt_path
        elif version == "SA":
            from builder.SAGXT import SAGXT
            generator = SAGXT()
            if not generator.load_text(output_txt_path):
                QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_loading_text"))
                return
            # 直接生成最终GXT文件
            if self.gxt_file_path:
                base_name = os.path.splitext(os.path.basename(self.gxt_file_path))[0]
                final_gxt_path = os.path.join(gxt_dir, f"{base_name}.gxt")
            else:
                base_name = os.path.splitext(os.path.basename(self.gxt_txt_path or ""))[0]
                final_gxt_path = os.path.join(gxt_dir, f"{base_name}.gxt")
            generator.save_as_gxt(final_gxt_path)
            generated_gxt_path = final_gxt_path
        elif version == "IV":
            from builder.IVGXT import generate_gxt
            try:
                # 直接生成最终GXT文件
                if self.gxt_file_path:
                    base_name = os.path.splitext(os.path.basename(self.gxt_file_path))[0]
                    final_gxt_path = os.path.join(gxt_dir, f"{base_name}.gxt")
                else:
                    base_name = os.path.splitext(os.path.basename(self.gxt_txt_path or ""))[0]
                    final_gxt_path = os.path.join(gxt_dir, f"{base_name}.gxt")
                generate_gxt(output_txt_path, final_gxt_path)
                generated_gxt_path = final_gxt_path
            except Exception as e:
                self.version_icon_label.setVisible(False)
                QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_running_builder", error=str(e)))
                return
        else:
            self.version_icon_label.setVisible(False)
            QMessageBox.critical(self, self.tr("error_messages"), self.tr("error_unknown_gxt_version"))
            return

        # 保存到txt或gxt同目录
        if self.gxt_file_path:
            base_name = os.path.splitext(os.path.basename(self.gxt_file_path))[0]
            # 备份原始GXT文件
            backup_gxt_path = os.path.join(gxt_dir, f"{base_name}_backup.gxt")
            shutil.copy(self.gxt_file_path, backup_gxt_path)
            # 替换原始GXT文件（如果生成的文件和目标文件不是同一个文件）
            try:
                if not os.path.samefile(generated_gxt_path, self.gxt_file_path):
                    shutil.copy(generated_gxt_path, self.gxt_file_path)
            except FileNotFoundError:
                # 如果文件不存在，则直接复制
                shutil.copy(generated_gxt_path, self.gxt_file_path)
            QMessageBox.information(self, self.tr("prompt_messages"), self.tr("info_file_saved", path=self.gxt_file_path, backup_path=backup_gxt_path))
        else:
            base_name = os.path.splitext(os.path.basename(self.gxt_txt_path or ""))[0]
            # 生成同名GXT文件并备份原始文件（如果存在）
            new_gxt_path = os.path.join(gxt_dir, f"{base_name}.gxt")
            # 注意：这里不需要复制，因为文件已经直接生成在目标位置
            QMessageBox.information(self, self.tr("prompt_messages"), self.tr("info_gxt_saved", path=new_gxt_path))

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
        base_size = 18  # 减小按钮尺寸以适应行高
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
        
        # 获取最新的行映射数据，确保定位准确
        current_row_section_map = self.get_current_row_section_map()
        
        # 滚动到对应的表格行
        if section_name in current_row_section_map:
            row = current_row_section_map[section_name]
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
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: rgba(235, 248, 255, 0.7);
                }
                QPushButton:checked {
                    background: rgba(66, 153, 225, 0.7);
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
        # 使用统一的样式定义，让Qt自动处理checked状态
        self.regex_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(240, 240, 240, 0.7);
                border: 1px solid rgba(203, 213, 224, 0.7);
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                padding: 0px;
                min-width: 32px;
                max-width: 32px;
                min-height: 32px;
                max-height: 32px;
            }
            QPushButton:checked {
                background-color: rgba(66, 153, 225, 0.8);
                color: white;
                border: 1px solid rgba(66, 153, 225, 0.8);
            }
        """)
        # 重新设置按钮尺寸，防止在某些情况下按钮尺寸变化
        self.regex_button.setFixedSize(32, 32)
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
                if row % 100 == 0:  # 每100行处理一次事件（提高性能）
                    QApplication.processEvents()
        elif self.regex_mode and not regex_valid:
            # 正则表达式无效，隐藏所有行
            for row in range(self.output_table.rowCount()):
                result_cache[row] = True
                self.output_table.setRowHidden(row, True)
                # 处理事件队列，使界面更新更流畅
                if row % 100 == 0:  # 每100行处理一次事件（提高性能）
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
                if row % 100 == 0:  # 每100行处理一次事件（提高性能）
                    QApplication.processEvents()

        # 更新缓存（限制缓存大小）
        if len(self.search_cache) > 50:  # 限制缓存大小为50个搜索词
            self.search_cache.clear()
        self.search_cache[cache_key] = result_cache

    def safe_add_row(self, row):
        """安全地在指定行后插入一行（用于表格按钮）"""
        self.output_table.insertRow(row + 1)
        for col in range(self.output_table.columnCount()):
            item = QTableWidgetItem("")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            if col == 1:  # Value列使用自定义字体
                item.setFont(self.value_column_font)
            # 初始化新插入行的历史记录
            self.table_item_history.set_last_text(item, "")
            self.output_table.setItem(row + 1, col, item)
        # 明确设置新插入行的行高为32像素
        self.output_table.setRowHeight(row + 1, 32)
        # 插入行后强制更新表名定位
        self.sync_sections_to_sidebar()

    def safe_delete_row(self, row):
        """安全地删除指定行（用于表格按钮）"""
        if 0 <= row < self.output_table.rowCount():
            self.output_table.removeRow(row)
            # 删除行后强制更新表名定位
            self.sync_sections_to_sidebar()

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
        
        # 显示表格并隐藏占位符
        self.output_table.setVisible(True)
        self.placeholder_label.setVisible(False)

        # 清空搜索缓存，因为表格内容已更改
        self.search_cache.clear()
        self.table_data_cache = []

        # 清空搜索缓存，当表格内容更改时同时清除正则模式下的缓存
        self.regex_mode = False
        self.regex_button.setChecked(False)
        self.regex_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(240, 240, 240, 0.7);
                border: 1px solid rgba(203, 213, 224, 0.7);
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                padding: 0px;
                min-width: 32px;
                max-width: 32px;
                min-height: 32px;
                max-height: 32px;
            }
            QPushButton:checked {
                background-color: rgba(66, 153, 225, 0.8);
                color: white;
                border: 1px solid rgba(66, 153, 225, 0.8);
            }
        """)
        # 确保按钮尺寸始终保持32x32
        self.regex_button.setFixedSize(32, 32)

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
                # 解除表名编辑限制，允许用户编辑表名
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable)
                item.setFont(font_bold)
                # 初始化表名监测的文本记录
                self.table_item_history.set_last_text(item, line)
                self.output_table.setItem(idx, 0, item)
                self.output_table.setItem(idx, 1, QTableWidgetItem(""))
            elif typ == 'kv':
                eq = line.find('=')
                key = line[:eq].strip()
                value = line[eq+1:].strip()
                key_item = QTableWidgetItem(key)
                value_item = QTableWidgetItem(value)
                key_item.setFont(font_normal)
                value_item.setFont(self.value_column_font)  # 使用自定义字体
                # 初始化文本记录用于修改监测
                self.table_item_history.set_last_text(key_item, key)
                self.table_item_history.set_last_text(value_item, value)
                self.output_table.setItem(idx, 0, key_item)
                self.output_table.setItem(idx, 1, value_item)
            # 明确设置每行的行高为32像素
            self.output_table.setRowHeight(idx, 32)

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
            widget.setStyleSheet("QWidget#btn_container { background: transparent; }")  # 只对容器设置透明背景
            widget.setObjectName("btn_container")  # 设置对象名称以精确控制样式
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
            layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            widget.setFixedHeight(32)  # 明确设置控件高度为32像素
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

        class CharacterTooltipEventFilter(QtCore.QObject):
            """字符级提示事件过滤器，用于在表格value列显示字符的hex值"""
            
            def __init__(self, table_widget, main_window):
                super().__init__()
                self.table_widget = table_widget
                self.main_window = main_window
                
            def eventFilter(self, obj, event):
                # 处理按键事件
                if event.type() == QtCore.QEvent.Type.KeyPress:
                    # 检查是否按下了Alt键
                    if event.key() == Qt.Key.Key_Alt:
                        self.main_window.show_selected_char_info()
                        return True  # 返回True表示事件已处理，防止进一步传播
                        
                return super().eventFilter(obj, event)

        class TableItemEditEventFilter(QtCore.QObject):
            """表格项编辑事件过滤器，用于监测表名修改"""
            
            def __init__(self, table_widget, main_window):
                super().__init__()
                self.table_widget = table_widget
                self.main_window = main_window
                self.last_edit_text = ""
                
            def eventFilter(self, obj, event):
                # 检查是否是编辑开始事件
                if event.type() == QtCore.QEvent.Type.FocusIn:
                    if isinstance(obj, QtWidgets.QLineEdit):
                        # 保存编辑前的文本
                        self.last_edit_text = obj.text()
                
                # 检查是否是编辑完成事件
                elif event.type() == QtCore.QEvent.Type.FocusOut:
                    # 检查对象是否是表格项编辑器
                    if isinstance(obj, QtWidgets.QLineEdit):
                        # 检查编辑器是否属于我们的表格
                        parent = obj.parent()
                        while parent:
                            if parent == self.table_widget:
                                current_text = obj.text()
                                # 检查文本是否发生了变化
                                if current_text != self.last_edit_text:
                                    # 检查是否是表名相关的修改
                                    if (self.last_edit_text.startswith('[') and self.last_edit_text.endswith(']') or
                                        current_text.startswith('[') and current_text.endswith(']')):
                                        # 触发表名同步检查
                                        self.main_window.sync_sections_to_sidebar()
                                break
                            parent = parent.parent()
                
                return False

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
                            # 移除对表名行的特殊处理，允许表名行也显示编辑按钮
                            self.table.setCellWidget(row, 2, self.get_btn_widget(row))
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
        
        # 安装字符提示事件过滤器
        if hasattr(self, "_char_tooltip_filter") and self._char_tooltip_filter:
            self.output_table.removeEventFilter(self._char_tooltip_filter)
        self._char_tooltip_filter = CharacterTooltipEventFilter(self.output_table, self)
        self.output_table.installEventFilter(self._char_tooltip_filter)
        
        # 安装表格项编辑事件过滤器
        if hasattr(self, "_table_item_edit_filter") and self._table_item_edit_filter:
            self.output_table.removeEventFilter(self._table_item_edit_filter)
        self._table_item_edit_filter = TableItemEditEventFilter(self.output_table, self)
        self.output_table.installEventFilter(self._table_item_edit_filter)
        
        # 连接表格项修改信号
        self.output_table.itemChanged.connect(self.on_table_item_changed)
        # --- 结束 ---

        # 移除对section_combobox的引用，因为我们现在使用侧边栏导航
        # self.section_combobox.currentIndexChanged.connect(
        #     lambda idx: self.scroll_to_section(idx, row_section_map)
        # )

    def show_selected_char_info(self):
        """显示选中字符的信息，通过Alt+X快捷键触发"""
        # 首先检查是否有焦点控件（编辑状态）
        focused_widget = QtWidgets.QApplication.focusWidget()
        
        # 检查是否是表格中的LineEdit编辑器
        if isinstance(focused_widget, QtWidgets.QLineEdit):
            # 检查是否有选中文本
            if focused_widget.hasSelectedText():
                selected_text = focused_widget.selectedText()
                if selected_text:
                    # 只显示第一个选中字符的信息
                    char = selected_text[0]
                    hex_value = f"0x{ord(char):04X}"
                    cursor_pos = QtGui.QCursor.pos()
                    self.char_tooltip.showText(
                        cursor_pos,
                        f"字符: {char}\nUnicode: {hex_value}"
                    )
                    return
        
        # 如果没有在编辑状态或没有选中文本，回退到处理选中的表格项
        selected_items = self.output_table.selectedItems()
        if not selected_items:
            return
            
        # 处理选中的表格项
        for item in selected_items:
            col = item.column()
            row = item.row()
            
            # 确保是在value列且不是section行
            item_text = item.text() if item else ""
            if col == 1 and item_text:
                # 检查是否为section行
                section_item = self.output_table.item(row, 0)
                section_text = section_item.text() if section_item else ""
                if not (section_text.startswith('[') and section_text.endswith(']')):
                    # 直接使用单元格文本的第一个字符
                    char = item_text[0]
                    hex_value = f"0x{ord(char):04X}"
                    cursor_pos = QtGui.QCursor.pos()
                    self.char_tooltip.showText(
                        cursor_pos,
                        f"字符: {char}\nUnicode: {hex_value}"
                    )
                    return

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

    def on_table_item_changed(self, item):
        """处理表格项修改事件，监测表名修改"""
        if item.column() == 0:  # 只监测Key列的修改
            row = item.row()
            key_item = self.output_table.item(row, 0)
            
            if key_item:
                key_text = key_item.text()
                
                # 获取修改前的文本
                old_text = self.table_item_history.get_last_text(item)
                
                # 检查表名修改的各种情况
                is_section_now = key_text.startswith('[') and key_text.endswith(']')
                was_section_before = old_text.startswith('[') and old_text.endswith(']')
                
                # 情况1：从普通文本变成表名（新增表）
                if not was_section_before and is_section_now:
                    section_name = key_text[1:-1]
                    if self.validate_section_name(section_name):
                        # 设置表名粗体字体
                        font_bold = QFont()
                        font_bold.setBold(True)
                        key_item.setFont(font_bold)
                        # 识别为新表，同步到侧边栏
                        self.sync_sections_to_sidebar()
                        self.status_message_label.setText(f"新增表: {section_name}")
                        QtCore.QTimer.singleShot(2000, lambda: self.status_message_label.setText(""))
                
                # 情况2：从表名变成普通文本（删除表）
                elif was_section_before and not is_section_now:
                    old_section_name = old_text[1:-1]
                    self.sync_sections_to_sidebar()
                    self.status_message_label.setText(f"移除表: {old_section_name}")
                    QtCore.QTimer.singleShot(2000, lambda: self.status_message_label.setText(""))
                
                # 情况3：表名被修改（重命名表）
                elif was_section_before and is_section_now:
                    old_section_name = old_text[1:-1]
                    new_section_name = key_text[1:-1]
                    if old_section_name != new_section_name:
                        if self.validate_section_name(new_section_name):
                            # 处理表名重命名
                            if self.handle_section_rename(old_section_name, new_section_name):
                                self.status_message_label.setText(f"表名修改: {old_section_name} → {new_section_name}")
                                QtCore.QTimer.singleShot(2000, lambda: self.status_message_label.setText(""))
                        else:
                            # 表名无效，恢复原表名
                            key_item.setText(old_text)
                            self.status_message_label.setText("表名包含非法字符，已恢复")
                            QtCore.QTimer.singleShot(2000, lambda: self.status_message_label.setText(""))
                
                # 保存当前文本作为下次比较的基准
                self.table_item_history.set_last_text(item, key_text)

    def sync_sections_to_sidebar(self):
        """同步表格中的表名到侧边栏"""
        # 从表格中提取所有表名
        section_names = []
        row_section_map = {}
        
        for row in range(self.output_table.rowCount()):
            key_item = self.output_table.item(row, 0)
            if key_item:
                key_text = key_item.text()
                # 检查是否是表名（以[]包围的文本）
                if key_text.startswith('[') and key_text.endswith(']'):
                    section_name = key_text[1:-1]  # 去掉方括号
                    section_names.append(section_name)
                    row_section_map[section_name] = row
        
        # 检查是否有新的表名出现
        current_sections = set(section_names)
        old_sections = set(name for _, name in self.section_buttons)
        
        # 检测新增的表名
        new_sections = current_sections - old_sections
        removed_sections = old_sections - current_sections
        
        # 如果表名有变化，重新创建侧边栏按钮
        if current_sections != old_sections:
            self.create_sidebar_buttons(section_names, row_section_map)
            
            # 更新解析内容以反映新的表名结构
            self.update_parsed_content_from_table()
            
            # 显示状态消息，区分修改和新增
            if new_sections:
                self.status_message_label.setText(f"新增 {len(new_sections)} 个表，共 {len(section_names)} 个表")
            elif removed_sections:
                self.status_message_label.setText(f"移除 {len(removed_sections)} 个表，共 {len(section_names)} 个表")
            else:
                self.status_message_label.setText(f"表名已同步到侧边栏，共 {len(section_names)} 个表")
            
            QtCore.QTimer.singleShot(3000, lambda: self.status_message_label.setText(""))

    def detect_new_sections(self, current_sections, old_sections):
        """检测新出现的表名"""
        new_sections = current_sections - old_sections
        if new_sections:
            return list(new_sections)
        return []

    def validate_section_name(self, section_name):
        """验证表名是否有效"""
        # 表名不能为空
        if not section_name.strip():
            return False
        
        # 表名不能包含非法字符
        invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
        for char in invalid_chars:
            if char in section_name:
                return False
        
        return True

    def detect_and_handle_new_sections(self):
        """检测并处理新出现的表名"""
        # 从表格中提取所有表名
        section_names = []
        row_section_map = {}
        
        for row in range(self.output_table.rowCount()):
            key_item = self.output_table.item(row, 0)
            if key_item:
                key_text = key_item.text()
                # 检查是否是表名（以[]包围的文本）
                if key_text.startswith('[') and key_text.endswith(']'):
                    section_name = key_text[1:-1]  # 去掉方括号
                    if self.validate_section_name(section_name):
                        section_names.append(section_name)
                        row_section_map[section_name] = row
        
        # 检查是否有新的表名出现
        current_sections = set(section_names)
        old_sections = set(name for _, name in self.section_buttons)
        
        # 检测新增和删除的表名
        new_sections = current_sections - old_sections
        removed_sections = old_sections - current_sections
        
        # 如果有变化，进行同步
        if new_sections or removed_sections:
            self.sync_sections_to_sidebar()
            return True
        
        return False

    def handle_section_rename(self, old_name, new_name):
        """处理表名重命名"""
        # 验证新表名是否有效
        if not self.validate_section_name(new_name):
            # 如果无效，恢复原表名
            return False
        
        # 更新侧边栏按钮
        for i, (button, name) in enumerate(self.section_buttons):
            if name == old_name:
                button.setText(new_name)
                # 更新按钮连接
                button.clicked.disconnect()
                button.clicked.connect(lambda checked, name=new_name: self.on_sidebar_button_clicked(name, self.get_current_row_section_map()))
                # 更新按钮列表
                self.section_buttons[i] = (button, new_name)
                break
        
        # 更新解析内容
        self.update_parsed_content_from_table()
        
        return True

    def get_current_row_section_map(self):
        """获取当前表格的行与表名的映射关系"""
        row_section_map = {}
        
        for row in range(self.output_table.rowCount()):
            key_item = self.output_table.item(row, 0)
            if key_item:
                key_text = key_item.text()
                if key_text.startswith('[') and key_text.endswith(']'):
                    section_name = key_text[1:-1]
                    row_section_map[section_name] = row
        
        return row_section_map

    def show_background_settings(self):
        """显示背景设置对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("背景设置")
        dialog.setModal(True)
        dialog.resize(400, 400)
        
        layout = QVBoxLayout(dialog)
        
        # 标题
        title_label = QLabel("选择背景图片")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px 0;")
        layout.addWidget(title_label)
        
        # 预设背景选项
        preset_group = QGroupBox("预设背景")
        preset_layout = QVBoxLayout(preset_group)
        
        # 无背景选项
        no_background_btn = QPushButton("无背景（默认）")
        no_background_btn.clicked.connect(lambda: self.set_background(None))
        preset_layout.addWidget(no_background_btn)
        
        # 添加自定义背景按钮
        custom_background_btn = QPushButton("选择自定义图片...")
        custom_background_btn.clicked.connect(self.select_custom_background)
        preset_layout.addWidget(custom_background_btn)
        
        layout.addWidget(preset_group)
        
        # 背景效果设置
        effects_group = QGroupBox("背景效果设置")
        effects_layout = QVBoxLayout(effects_group)
        
        # 高斯模糊半径标签和滑块
        blur_radius_layout = QHBoxLayout()
        blur_radius_label = QLabel("高斯模糊半径:")
        self.blur_radius_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.blur_radius_slider.setRange(0, 50)  # 0-50像素模糊半径
        current_blur_value = getattr(self, '_blur_radius_value', 0)
        self.blur_radius_slider.setValue(current_blur_value)  # 设置当前保存的模糊值
        
        # 显示当前模糊半径值的标签
        self.blur_radius_value_label = QLabel(str(current_blur_value))
        self.blur_radius_value_label.setFixedWidth(30)
        
        # 连接滑块值变化信号
        self.blur_radius_slider.valueChanged.connect(
            lambda value: self.blur_radius_value_label.setText(str(value))
        )
        
        # 连接滑块值变化信号以更新预览和存储值
        self.blur_radius_slider.valueChanged.connect(
            lambda value: self._on_blur_radius_changed(value)
        )
        
        blur_radius_layout.addWidget(blur_radius_label)
        blur_radius_layout.addWidget(self.blur_radius_slider)
        blur_radius_layout.addWidget(self.blur_radius_value_label)
        
        effects_layout.addLayout(blur_radius_layout)
        
        # 亮度调整标签和滑块
        brightness_layout = QHBoxLayout()
        brightness_label = QLabel("亮度调整:")
        self.brightness_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(-100, 100)  # -100到100的亮度调整范围
        current_brightness_value = getattr(self, '_brightness_value', 0)
        self.brightness_slider.setValue(current_brightness_value)  # 设置当前保存的亮度值
        
        # 显示当前亮度值的标签
        self.brightness_value_label = QLabel(str(current_brightness_value))
        self.brightness_value_label.setFixedWidth(30)
        
        # 创建亮度调整延时定时器
        self.brightness_timer = QtCore.QTimer(self)
        self.brightness_timer.setSingleShot(True)
        self.brightness_timer.timeout.connect(self._apply_brightness_change)
        
        # 连接滑块值变化信号 - 更新显示值并启动延时
        self.brightness_slider.valueChanged.connect(self._on_brightness_value_changed)
        
        # 连接滑块释放信号 - 松手后立即应用效果
        self.brightness_slider.sliderReleased.connect(self._on_brightness_slider_released)
        
        brightness_layout.addWidget(brightness_label)
        brightness_layout.addWidget(self.brightness_slider)
        brightness_layout.addWidget(self.brightness_value_label)
        
        effects_layout.addLayout(brightness_layout)
        layout.addWidget(effects_group)
        
        # 预览区域
        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.background_preview = QLabel()
        self.background_preview.setMinimumHeight(150)
        self.background_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.background_preview.setStyleSheet("border: 1px solid #ccc; border-radius: 5px;")
        self.update_background_preview()
        preview_layout.addWidget(self.background_preview)
        
        layout.addWidget(preview_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(lambda: self.save_effects_settings_and_close(dialog))
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()

    def save_effects_settings_and_close(self, dialog):
        """保存效果设置并关闭对话框"""
        # 确保模糊半径值被保存
        if hasattr(self, 'blur_radius_slider'):
            self._blur_radius_value = self.blur_radius_slider.value()
            
        # 确保亮度值被保存
        if hasattr(self, 'brightness_slider'):
            self._brightness_value = self.brightness_slider.value()
        
        # 保存当前的背景设置（包括模糊半径）
        current_background = None
        if self.background_pixmap:
            # 如果有背景图片，需要找到其路径
            # 由于我们没有直接存储路径，这里需要从配置文件中读取
            if os.path.exists("background_settings.json"):
                try:
                    with open("background_settings.json", "r", encoding="utf-8") as f:
                        settings = json.load(f)
                        current_background = settings.get("background_image")
                except:
                    pass
        
        self.save_background_setting(current_background)
        
        # 应用亮度设置到主窗口背景
        self.update()
        
        dialog.accept()

    def select_custom_background(self):
        """选择自定义背景图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择背景图片", 
            "", 
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            self.set_background(file_path)

    def set_background(self, image_path):
        """设置背景图片"""
        if image_path is None:
            # 移除背景
            self.background_pixmap = None
            self.save_background_setting(None)
        else:
            # 加载新背景
            pixmap = QtGui.QPixmap(image_path)
            if not pixmap.isNull():
                self.background_pixmap = pixmap
                self.save_background_setting(image_path)
            else:
                QMessageBox.warning(self, "错误", "无法加载图片文件")
                return
        
        # 更新预览
        self.update_background_preview()
        
        # 更新窗口背景
        self.update()

    def _on_blur_radius_changed(self, value):
        """处理模糊半径变化"""
        # 存储模糊半径值为实例变量
        self._blur_radius_value = value
        # 更新预览
        if hasattr(self, 'background_preview'):
            self.update_background_preview()
        # 更新窗口背景
        self.update()

    def _on_brightness_value_changed(self, value):
        """滑块值变化时的处理 - 更新显示并启动延时"""
        # 更新显示值
        self.brightness_value_label.setText(str(value))
        
        # 如果正在拖拽，启动延时定时器
        if hasattr(self, 'brightness_timer'):
            self.brightness_timer.stop()  # 停止之前的定时器
            self.brightness_timer.start(800)  # 800ms延时，给用户足够时间调整
    
    def _on_brightness_slider_released(self):
        """滑块松手后立即应用"""
        # 停止延时定时器
        if hasattr(self, 'brightness_timer'):
            self.brightness_timer.stop()
        
        # 立即应用当前值
        self._apply_brightness_change()
    
    def _apply_brightness_change(self):
        """延时应用亮度变化 - 仅更新预览"""
        # 获取当前滑块值
        if hasattr(self, 'brightness_slider'):
            value = self.brightness_slider.value()
            # 存储亮度值为实例变量
            self._brightness_value = value
            # 仅更新预览，不更新主窗口背景
            if hasattr(self, 'background_preview'):
                self.update_background_preview()
    
    def _on_brightness_changed(self, value):
        """处理亮度变化（保留用于兼容性）- 仅更新预览"""
        # 存储亮度值为实例变量
        self._brightness_value = value
        # 仅更新预览，不更新主窗口背景
        if hasattr(self, 'background_preview'):
            self.update_background_preview()

    def update_background_preview(self):
        """更新背景预览"""
        if not hasattr(self, 'background_preview'):
            return
            
        if self.background_pixmap:
            # 缩放图片以适应预览区域
            preview_pixmap = self.background_pixmap.scaled(
                300, 100, 
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # 应用模糊效果预览
            blur_radius = getattr(self, '_blur_radius_value', 0)
                
            if blur_radius > 0:
                # 创建模糊效果
                blur_effect = QtWidgets.QGraphicsBlurEffect()
                blur_effect.setBlurRadius(blur_radius)
                
                # 创建临时场景用于模糊效果
                scene = QtWidgets.QGraphicsScene()
                item = QtWidgets.QGraphicsPixmapItem(preview_pixmap)
                item.setGraphicsEffect(blur_effect)
                scene.addItem(item)
                
                # 渲染模糊后的图片
                blurred_image = QtGui.QImage(
                    preview_pixmap.size(), 
                    QtGui.QImage.Format.Format_ARGB32
                )
                blurred_image.fill(QtCore.Qt.GlobalColor.transparent)
                blur_painter = QtGui.QPainter(blurred_image)
                scene.render(blur_painter)
                blur_painter.end()
                
                preview_pixmap = QtGui.QPixmap.fromImage(blurred_image)
            
            # 应用亮度调整（在预览中使用更小的步长以提高性能）
            brightness = getattr(self, '_brightness_value', 0)
            if brightness != 0:
                preview_image = preview_pixmap.toImage()
                preview_image = self._adjust_brightness(preview_image, brightness)
                preview_pixmap = QtGui.QPixmap.fromImage(preview_image)
            
            self.background_preview.setPixmap(preview_pixmap)
            self.background_preview.setText("")
        else:
            self.background_preview.setPixmap(QtGui.QPixmap())
            self.background_preview.setText("无背景")

    def save_background_setting(self, image_path):
        """保存背景设置到配置文件"""
        settings = {}
        if os.path.exists("background_settings.json"):
            try:
                with open("background_settings.json", "r", encoding="utf-8") as f:
                    settings = json.load(f)
            except:
                settings = {}
        
        settings["background_image"] = image_path
        
        # 保存模糊半径设置
        settings["blur_radius"] = getattr(self, '_blur_radius_value', 0)
        
        # 保存亮度设置
        settings["brightness"] = getattr(self, '_brightness_value', 0)
        
        try:
            with open("background_settings.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存背景设置失败: {e}")

    def update_version_icon(self, version):
        """根据GXT版本更新状态栏图标"""
        if not version:
            self.version_icon_label.setVisible(False)
            return
            
        icon_path = ""
        if version == "III":
            icon_path = "./icons/III.ico"
        elif version == "VC":
            icon_path = "./icons/VC.ico"
        elif version == "SA":
            icon_path = "./icons/SA.ico"
        elif version == "IV":
            icon_path = "./icons/IV.png"
        
        if icon_path and os.path.exists(icon_path):
            try:
                pixmap = QtGui.QPixmap(icon_path)
                if not pixmap.isNull():
                    # 缩放图标到合适大小，保持宽高比
                    scaled_pixmap = pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.version_icon_label.setPixmap(scaled_pixmap)
                    self.version_icon_label.setToolTip(f"GXT版本: {version}")
                    self.version_icon_label.setVisible(True)
                    print(f"成功加载版本图标: {icon_path}")
                else:
                    print(f"图标文件无效: {icon_path}")
                    self.version_icon_label.setVisible(False)
            except Exception as e:
                print(f"加载图标失败: {icon_path}, 错误: {e}")
                self.version_icon_label.setVisible(False)
        else:
            print(f"图标文件不存在: {icon_path}")
            self.version_icon_label.setVisible(False)

    def load_background_settings(self):
        """加载背景设置"""
        if os.path.exists("background_settings.json"):
            try:
                with open("background_settings.json", "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    image_path = settings.get("background_image")
                    if image_path and os.path.exists(image_path):
                        self.background_pixmap = QtGui.QPixmap(image_path)
                    elif image_path is None:
                        self.background_pixmap = None
                    
                    # 加载模糊半径设置
                    self._blur_radius_value = settings.get("blur_radius", 0)
                    
                    # 加载亮度设置
                    self._brightness_value = settings.get("brightness", 0)
                    
                    # 如果滑块存在，也更新滑块的值
                    if hasattr(self, 'blur_radius_slider'):
                        self.blur_radius_slider.setValue(self._blur_radius_value)
                    if hasattr(self, 'brightness_slider'):
                        self.brightness_slider.setValue(self._brightness_value)
            except Exception as e:
                print(f"加载背景设置失败: {e}")
                self.background_pixmap = None

    def show_font_settings(self):
        """显示字体设置对话框"""
        # 获取当前Value列的字体
        current_font = self.value_column_font
        
        # 打开系统字体选择对话框
        font, ok = QFontDialog.getFont(current_font, self, "选择Value列字体")
        
        if ok:
            # 保存新字体设置
            self.value_column_font = font
            
            # 应用字体到当前表格的所有Value列项
            self.apply_font_to_value_column()
            
            # 保存字体设置到配置文件
            self.save_font_settings()
            
            # 显示成功消息
            QMessageBox.information(self, "字体设置", f"字体已更新为: {font.family()}, 大小: {font.pointSize()}")

    def apply_font_to_value_column(self):
        """将字体应用到表格Value列的所有项"""
        if not hasattr(self, 'output_table') or self.output_table.rowCount() == 0:
            return
            
        # 设置字体渲染策略以提高质量
        self.value_column_font.setStyleStrategy(
            QtGui.QFont.StyleStrategy.PreferAntialias | 
            QtGui.QFont.StyleStrategy.PreferQuality
        )
            
        # 遍历表格的所有行，更新Value列（第1列）的字体
        for row in range(self.output_table.rowCount()):
            value_item = self.output_table.item(row, 1)  # Value列是第1列
            if value_item:
                value_item.setFont(self.value_column_font)

    def save_font_settings(self):
        """保存字体设置到配置文件"""
        settings = {}
        if os.path.exists("font_settings.json"):
            try:
                with open("font_settings.json", "r", encoding="utf-8") as f:
                    settings = json.load(f)
            except:
                settings = {}
        
        # 保存字体信息
        settings["value_column_font"] = {
            "family": self.value_column_font.family(),
            "pointSize": self.value_column_font.pointSize(),
            "weight": self.value_column_font.weight(),
            "style": self.value_column_font.styleName(),
            "italic": self.value_column_font.italic(),
            "bold": self.value_column_font.bold()
        }
        
        try:
            with open("font_settings.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存字体设置失败: {e}")

    def load_font_settings(self):
        """加载字体设置"""
        if os.path.exists("font_settings.json"):
            try:
                with open("font_settings.json", "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    font_info = settings.get("value_column_font")
                    if font_info:
                        font = QFont()
                        font.setFamily(font_info.get("family", "Microsoft YaHei UI"))
                        font.setPointSize(font_info.get("pointSize", 10))
                        font.setWeight(font_info.get("weight", QFont.Weight.Normal))
                        font.setItalic(font_info.get("italic", False))
                        font.setBold(font_info.get("bold", True))
                        if "style" in font_info:
                            font.setStyleName(font_info["style"])
                        self.value_column_font = font
            except Exception as e:
                print(f"加载字体设置失败: {e}")
                # 使用默认字体
                self.value_column_font = QFont()
                self.value_column_font.setBold(True)

    def _adjust_brightness(self, image, brightness):
        """真正的亮度调整 - 直接修改像素RGB值"""
        # 只有在需要调整时才处理
        if brightness == 0:
            return image
            
        # 创建结果图像
        result_image = QtGui.QImage(image.size(), QtGui.QImage.Format.Format_ARGB32)
        
        # 计算亮度调整因子 (-100到100映射到0.0到2.0)
        # brightness = -100 -> factor = 0.0 (全黑)
        # brightness = 0 -> factor = 1.0 (原始)
        # brightness = 100 -> factor = 2.0 (双倍亮度)
        brightness_factor = 1.0 + (brightness / 100.0)
        
        # 确保因子在合理范围内
        brightness_factor = max(0.0, min(3.0, brightness_factor))
        
        # 逐像素处理
        width = image.width()
        height = image.height()
        
        for y in range(height):
            for x in range(width):
                # 获取原始像素颜色
                pixel = image.pixel(x, y)
                color = QtGui.QColor(pixel)
                
                # 获取RGBA值
                r, g, b, a = color.red(), color.green(), color.blue(), color.alpha()
                
                # 调整RGB值（保持Alpha不变）
                new_r = min(255, max(0, int(r * brightness_factor)))
                new_g = min(255, max(0, int(g * brightness_factor)))
                new_b = min(255, max(0, int(b * brightness_factor)))
                
                # 设置新的像素颜色
                new_color = QtGui.QColor(new_r, new_g, new_b, a)
                result_image.setPixel(x, y, new_color.rgba())
        
        return result_image

    def paintEvent(self, event):
        """绘制背景"""
        # 先绘制背景
        if self.background_pixmap:
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
            
            # 缩放背景图片以适应窗口大小
            scaled_pixmap = self.background_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # 居中绘制
            x = (self.width() - scaled_pixmap.width()) // 2
            y = (self.height() - scaled_pixmap.height()) // 2
            
            # 检查是否需要应用高斯模糊
            blur_radius = 0
            # 安全地访问滑块值，避免访问已删除的对象
            if hasattr(self, '_blur_radius_value'):
                blur_radius = self._blur_radius_value
            
            # 如果需要模糊效果，则应用高斯模糊
            if blur_radius > 0:
                # 创建模糊效果
                blur_effect = QtWidgets.QGraphicsBlurEffect()
                blur_effect.setBlurRadius(blur_radius)
                
                # 创建临时的GraphicsScene用于应用模糊效果
                scene = QtWidgets.QGraphicsScene()
                item = QtWidgets.QGraphicsPixmapItem(scaled_pixmap)
                item.setGraphicsEffect(blur_effect)
                scene.addItem(item)
                
                # 将模糊后的图片绘制到pixmap上
                blurred_image = QtGui.QImage(
                    scaled_pixmap.size(), 
                    QtGui.QImage.Format.Format_ARGB32
                )
                blurred_image.fill(QtCore.Qt.GlobalColor.transparent)
                blur_painter = QtGui.QPainter(blurred_image)
                scene.render(blur_painter)
                blur_painter.end()
                
                # 使用模糊后的图片
                scaled_pixmap = QtGui.QPixmap.fromImage(blurred_image)
            
            # 应用亮度调整
            brightness = getattr(self, '_brightness_value', 0)
            if brightness != 0:
                image = scaled_pixmap.toImage()
                image = self._adjust_brightness(image, brightness)
                scaled_pixmap = QtGui.QPixmap.fromImage(image)
            
            # 绘制背景图片
            painter.drawPixmap(x, y, scaled_pixmap)
            painter.end()  # 确保正确结束绘制
        
        # 然后调用父类的paintEvent来绘制其他内容
        super().paintEvent(event)

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
            font: 600 28px 'Segoe UI'; /* 加粗大标题 */
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
            background: transparent;     /* 纯白背景突出内容 */
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
            background: transparent;     /* 纯白背景 */
            min-height: 24px;      /* 统一控件高度 */
        }
        /* 聚焦/悬停状态 - 高亮边框 */
        QLineEdit:focus, QComboBox:hover {
            border-color: #90CDF4; /* 浅蓝色反馈 */
        }

        /* ========== 数据表格 ==========
        设计目标：提升数据可读性，减少视觉疲劳 */
        QTableWidget {
            background: transparent;
            background: rgba(241, 245, 249, 0.3);
            border: 1px solid rgba(226, 232, 240, 0.3);
            border-radius: 12px;
            gridline-color: rgba(237, 242, 247, 0.3);
            alternate-background-color: rgba(247, 250, 252, 0.3);
            /* 启用字体平滑 */
            QTextEdit {
                qproperty-fontSmooth: true;
            }
        }
        /* 单元格样式 */
        QTableWidget::item {
            background: transparent;
            padding: 10px;
            border-bottom: 1px solid rgba(237, 242, 247, 0.3);
            /* 启用字体抗锯齿 */
            qproperty-textRenderHint: 1; /* 1 = Qt::TextAntialiasing */
            padding: 0px;            /* 去掉 Qt 默认内边距 */
        }
        /* 修正选中单元格文字颜色为黑色 */
        QTableWidget::item:selected {
            color: white !important;
            background: rgba(66, 153, 225, 0.7);
        }
        /* 编辑框半透明+模糊效果 */
        QTableWidget QLineEdit {
            background: rgba(255, 255, 255, 0.7);
            border: 2px solid rgba(99, 179, 237, 0.7);
            border-radius: 8px;
            padding: 8px;
            color: #222;
        }
        QTableWidget QLineEdit:focus {
            background: rgba(241, 245, 249, 0.7); /* 与侧边栏一致的透明度 */
            border: 2px solid rgba(49, 130, 206, 0.7); /* 与侧边栏一致的透明度 */
            color: #111;
        }

        #rowBtnContainer {
            background: transparent;
            border: none;
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

        /* 滚动条样式已移至全局样式 */
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
        
        /* ========== 全局滚动条样式 ========== */
        QScrollBar:vertical {
            background: #F1F5F9;
            width: 12px;
            margin: 2px 0 2px 0;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background: #BFD7ED;
            min-height: 30px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical:hover {
            background: #7BA7D7;
        }
        QScrollBar::handle:vertical:pressed {
            background: #5A8BC4;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            background: none;
            border: none;
            height: 0px;
        }
        QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
            width: 0; 
            height: 0;
            background: none;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: transparent;
        }
        
        QScrollBar:horizontal {
            background: #F1F5F9;
            height: 12px;
            margin: 0 2px 0 2px;
            border-radius: 6px;
        }
        QScrollBar::handle:horizontal {
            background: #BFD7ED;
            min-width: 30px;
            border-radius: 6px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #7BA7D7;
        }
        QScrollBar::handle:horizontal:pressed {
            background: #5A8BC4;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            background: none;
            border: none;
            width: 0px;
        }
        QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
            width: 0; 
            height: 0;
            background: none;
        }
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: transparent;
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