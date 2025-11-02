import os
import collections
import io
import struct
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QWidget, QSizePolicy, QSplitter,
    QFileDialog, QMessageBox, QComboBox, QCheckBox, QFontDialog, QSpinBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QFont, QFontDatabase, QFontMetricsF, QColor
from typing import List, Dict, Any, Callable, Union, Optional

class DebugMenuDialog(QDialog):
    def __init__(self, parent, actions):
        super().__init__(parent)
        self.setWindowTitle("GXT专业调试菜单")
        # 修正 PyQt6 WindowType 写法
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        self.setWindowState(Qt.WindowState.WindowNoState)
        self.setMinimumSize(900, 600)
        self.resize(900, 600)
        # 明确声明actions的类型
        self.actions: List[Dict[str, Any]] = actions
        self.save_btn: Optional[QPushButton] = None  # 声明 save_btn 属性
        self.version: Optional[str] = None  # 声明 version 属性
        self.char_positions: Dict[str, tuple] = {}  # 声明 char_positions 属性
        self.save_btn: Optional[QPushButton] = None  # 声明 save_btn 属性
        self.version: Optional[str] = None  # 声明 version 属性
        self.char_positions: Dict[str, tuple] = {}  # 声明 char_positions 属性
        self._init_ui()

    def _init_ui(self):
        # 应用样式表到调试菜单对话框，与主界面配色一致
        self.setStyleSheet("""
            QDialog {
                background: #F8FAFC;
                color: #2D3748;
                font-family: 'Microsoft YaHei UI', 'Microsoft YaHei';
                font-size: 14px;
                border: none;
            }
            QLabel {
                color: #2D3748;
                font-family: 'Microsoft YaHei UI', 'Microsoft YaHei';
                font-size: 14px;
                padding: 5px;
            }
            QPushButton {
                background: #4299E1;
                color: white;
                border-radius: 10px;
                padding: 8px 16px;
                min-width: 90px;
                font-family: 'Microsoft YaHei UI', 'Microsoft YaHei';
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                background: #3182CE;
            }
            QPushButton:pressed {
                background: #2B6CB0;
            }
            QPushButton:disabled {
                background: #CBD5E0;
                color: #718096;
            }
            QListWidget {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                font-family: 'Microsoft YaHei UI', 'Microsoft YaHei';
                font-size: 14px;
                color: #2D3748;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #EDF2F7;
            }
            QListWidget::item:selected {
                background: #BEE3F8;
                color: #2D3748;
                border-radius: 4px;
            }
            QTextEdit {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 14px;
                color: #2D3748;
                padding: 8px;
            }
            QComboBox {
                border: 2px solid #E2E8F0;
                border-radius: 10px;
                padding: 8px 12px;
                background: white;
                min-height: 28px;
                font-family: 'Microsoft YaHei UI', 'Microsoft YaHei';
                font-size: 14px;
                color: #2D3748;
            }
            QComboBox:hover {
                border-color: #90CDF4;
            }
            QComboBox::drop-down {
                width: 24px;
                border-left: 2px solid #E2E8F0;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #E2E8F0;
                background: white;
                selection-background-color: #BEE3F8;
                font-family: 'Microsoft YaHei UI', 'Microsoft YaHei';
                font-size: 14px;
                color: #2D3748;
            }
            QSpinBox {
                border: 2px solid #E2E8F0;
                border-radius: 10px;
                padding: 8px 12px;
                background: white;
                min-height: 28px;
                font-family: 'Microsoft YaHei UI', 'Microsoft YaHei';
                font-size: 14px;
                color: #2D3748;
                selection-background-color: #BEE3F8;
            }
            QSpinBox:hover {
                border-color: #90CDF4;
            }
            QSpinBox:focus {
                border-color: #4299E1;
                background: #EBF8FF;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 24px;
                border-left: 2px solid #E2E8F0;
                subcontrol-origin: border;
                background: transparent;
            }
            QSpinBox::up-button {
                border-top-right-radius: 10px;
            }
            QSpinBox::down-button {
                border-bottom-right-radius: 10px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #EBF8FF;
            }
            QSpinBox::up-arrow, QSpinBox::down-arrow {
                width: 10px;
                height: 10px;
                image: none;
            }
            QSpinBox::up-arrow {
                subcontrol-origin: padding;
                subcontrol-position: center;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2D3748, stop:1 #2D3748);
                width: 6px;
                height: 2px;
                border-radius: 1px;
            }
            QSpinBox::down-arrow {
                subcontrol-origin: padding;
                subcontrol-position: center;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2D3748, stop:1 #2D3748);
                width: 6px;
                height: 2px;
                border-radius: 1px;
            }
        """)

        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # 左侧菜单
        self.menu_list = QListWidget()
        self.menu_list.setMinimumWidth(220)
        self.menu_list.setMaximumWidth(320)
        self.menu_list.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        # 修复：self.actions是列表，不是函数，不应加()
        for action in self.actions:
            # 修复：根据DebugMenu中actions的结构访问属性
            item = QListWidgetItem(action["icon"], action["name"])
            item.setToolTip(action["tip"] if action["tip"] else "")
            self.menu_list.addItem(item)
        splitter.addWidget(self.menu_list)

        # 右侧内容区
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-weight:bold;font-size:18px;")
        self.title_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.content_layout.addWidget(self.title_label)
        self.text_edit = QTextEdit()
        #self.text_edit.setLineWrapMode(QTextEdit.NoWrap)
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.text_edit.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.text_edit.setStyleSheet("font-family: 'Microsoft YaHei', sans-serif !important; font-size: 13px;")
        self.text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.content_layout.addWidget(self.text_edit)
        splitter.addWidget(self.content_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([240, 660])

        # 按钮布局
        btn_layout = QHBoxLayout()
        
        # 保存图片按钮
        self.save_btn = QPushButton("保存图片")
        self.save_btn.clicked.connect(self._save_pixmap)
        self.save_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn_layout.addWidget(self.save_btn)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        self.content_layout.addLayout(btn_layout)

        self.menu_list.currentRowChanged.connect(self._on_menu_changed)
        self._on_menu_changed(0)

    def _on_menu_changed(self, idx):
        # 修复：self.actions是列表，不是函数，不应加()
        if idx < 0 or idx >= len(self.actions):
            return
        # 修复：self.actions是列表，不是函数，不应加()
        action = self.actions[idx]
        self.title_label.setText(action["name"])
        try:
            result = action["func"]()
            # 特殊处理码表编辑器界面
            if isinstance(result, tuple) and len(result) == 2 and result[0] == "码表编辑器界面":
                content, widgets = result
                # 隐藏文本编辑器和保存按钮
                self.text_edit.hide()
                if self.save_btn is not None:
                    self.save_btn.hide()
                
                # 清除旧的自定义组件
                for i in reversed(range(self.content_layout.count())):
                    item = self.content_layout.itemAt(i)
                    if item:
                        widget = item.widget()
                        if widget is not None and isinstance(widget, QLabel) and widget != self.title_label:
                            self.content_layout.removeWidget(widget)
                            widget.deleteLater()
                        elif widget is not None and widget not in [self.title_label, self.text_edit]:
                            # 检查是否是我们要保留的组件（标题标签和文本编辑器除外）
                            if widget != self.content_widget:
                                self.content_layout.removeWidget(widget)
                                widget.deleteLater()
                
                # 添加码表编辑器界面
                if widgets:
                    self.content_layout.insertWidget(1, widgets[0])
            elif isinstance(result, tuple) and len(result) == 2:
                content, pixmaps = result
                self.text_edit.setText(str(content) if content else "(无内容)")
                # 显示文本编辑器
                self.text_edit.show()
                # 清除旧图
                for i in reversed(range(self.content_layout.count())):
                    item = self.content_layout.itemAt(i)
                    if item:
                        widget = item.widget()
                        if widget is not None and isinstance(widget, QLabel) and widget != self.title_label:
                            self.content_layout.removeWidget(widget)
                            widget.deleteLater()
                        elif widget is not None and widget not in [self.title_label, self.text_edit]:
                            # 移除可能的其他自定义组件
                            if widget != self.content_widget:
                                self.content_layout.removeWidget(widget)
                                widget.deleteLater()
                # 添加新图
                for pix in pixmaps:
                    img_label = QLabel()
                    # 动态缩放图片以适应预览区域，保持原始比例且不超出边界
                    max_width = self.content_widget.width() - 16  # 预留边距
                    max_height = self.content_widget.height() - 16  # 预留边距
                    scaled_pix = pix.scaled(max_width, max_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    
                    # 创建深粉色背景的预览图
                    preview_pix = QPixmap(scaled_pix.size())
                    preview_pix.fill(Qt.GlobalColor.darkBlue)
                    painter = QPainter(preview_pix)
                    painter.drawPixmap(0, 0, scaled_pix)
                    painter.end()
                    
                    img_label.setPixmap(preview_pix)
                    img_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)  # 顶部对齐
                    img_label.setScaledContents(False)  # 禁止按比例缩放
                    img_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                    self.content_layout.insertWidget(self.content_layout.count()-3, img_label)
                # 保存当前图片引用
                self.current_pixmaps = pixmaps
                # 显示保存图片按钮（仅在字库贴图选项）
                if action["name"] == "字库贴图":
                    if self.save_btn is not None:
                        self.save_btn.show()
                else:
                    if self.save_btn is not None:
                        self.save_btn.hide()
            else:
                # 显示文本内容
                self.text_edit.setText(str(result) if result else "(无内容)")
                self.text_edit.show()
                # 清除旧图（当函数不返回图片时）
                for i in reversed(range(self.content_layout.count())):
                    item = self.content_layout.itemAt(i)
                    if item:
                        widget = item.widget()
                        if widget is not None and isinstance(widget, QLabel) and widget != self.title_label:
                            self.content_layout.removeWidget(widget)
                            widget.deleteLater()
                        elif widget is not None and widget not in [self.title_label, self.text_edit]:
                            # 移除可能的其他自定义组件
                            if widget != self.content_widget:
                                self.content_layout.removeWidget(widget)
                                widget.deleteLater()
                # 清除当前图片引用
                if hasattr(self, 'current_pixmaps'):
                    delattr(self, 'current_pixmaps')
                # 隐藏保存按钮
                if self.save_btn is not None:
                    self.save_btn.hide()
        except Exception as e:
            self.text_edit.setText(f"发生异常: {e}")
            self.text_edit.show()
            # 出现异常时也清除图片和其他自定义组件
            for i in reversed(range(self.content_layout.count())):
                item = self.content_layout.itemAt(i)
                if item:
                    widget = item.widget()
                    if widget is not None and isinstance(widget, QLabel) and widget != self.title_label:
                        self.content_layout.removeWidget(widget)
                        widget.deleteLater()
                    elif widget is not None and widget not in [self.title_label, self.text_edit]:
                        if widget != self.content_widget:
                            self.content_layout.removeWidget(widget)
                            widget.deleteLater()
            if hasattr(self, 'current_pixmaps'):
                delattr(self, 'current_pixmaps')
            # 隐藏保存按钮
            if self.save_btn is not None:
                self.save_btn.hide()
            
    def _save_pixmap(self):
        if not hasattr(self, 'current_pixmaps') or not self.current_pixmaps:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存图片", "", "PNG 图片 (*.png);;所有文件 (*)"
        )
        if file_path:
            try:
                self.current_pixmaps[0].save(file_path, "PNG")
                
                # 获取version和char_positions，优先从self获取，其次尝试从parent的debug_menu获取
                version = getattr(self, 'version', None)
                char_positions = getattr(self, 'char_positions', {})
                
                # 如果当前对象没有这些属性，尝试从parent获取
                if not version and hasattr(self, 'parent') and self.parent:
                    debug_menu = getattr(self.parent, 'debug_menu', None)
                    if debug_menu:
                        version = getattr(debug_menu, 'version', None)
                        char_positions = getattr(debug_menu, 'char_positions', {})
                
                # 如果是VC版本，询问是否生成.dat文件
                if version == "VC" and char_positions:
                    reply = QMessageBox.question(
                        self, '生成.dat文件', '是否要为VC版本生成.dat文件？',
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        try:
                            # 生成.dat文件路径（与PNG文件同目录）
                            png_dir = os.path.dirname(file_path)
                            png_name = os.path.splitext(os.path.basename(file_path))[0]
                            dat_path = os.path.join(png_dir, f"{png_name}.dat")
                            old_dat_path = os.path.join(png_dir, f"{png_name}.dat.old")
                            
                            # 备份原有的.dat文件
                            if os.path.exists(dat_path):
                                if os.path.exists(old_dat_path):
                                    os.remove(old_dat_path)
                                os.rename(dat_path, old_dat_path)
                            
                            # 创建65536个条目的数组，初始值为(63, 63)
                            dat_entries = [(63, 63)] * 0x10000
                            
                            # 更新实际字符的位置
                            for char, (row, col) in char_positions.items():
                                char_code = ord(char)
                                if 0 <= char_code < 0x10000:  # 确保字符编码在有效范围内
                                    dat_entries[char_code] = (row, col)
                            
                            # 写入.dat文件
                            with open(dat_path, 'wb') as dat_file:
                                for row, col in dat_entries:
                                    dat_file.write(struct.pack('BB', row, col))
                            
                            QMessageBox.information(self, "保存成功", f"图片已保存到：{file_path}\nVC版本对应的.dat文件已保存至: {dat_path}\n原有的.dat文件已备份为: {old_dat_path}")
                        except Exception as e:
                            QMessageBox.information(self, "保存成功", f"图片已保存到：{file_path}\n生成.dat文件时出错: {e}")
                    else:
                        QMessageBox.information(self, "保存成功", f"图片已保存到：{file_path}\n已跳过生成.dat文件")
                # 如果是IV版本，询问是否生成char_table.dat文件
                elif version == "IV" and char_positions:
                    reply = QMessageBox.question(
                        self, '生成char_table.dat文件', '是否要为IV版本生成char_table.dat文件？',
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        try:
                            # 生成char_table.dat文件路径（与PNG文件同目录）
                            png_dir = os.path.dirname(file_path)
                            dat_path = os.path.join(png_dir, "char_table.dat")
                            old_dat_path = os.path.join(png_dir, "char_table.dat.old")
                            
                            # 备份原有的char_table.dat文件
                            if os.path.exists(dat_path):
                                if os.path.exists(old_dat_path):
                                    os.remove(old_dat_path)
                                os.rename(dat_path, old_dat_path)
                            
                            # 按照IV版本格式写入char_table.dat文件
                            # 首先确保包含默认替换字符"？"
                            chars_list = list(char_positions.keys())
                            if '？' not in chars_list:
                                chars_list.insert(0, '？')
                            
                            # 写入char_table.dat文件
                            with open(dat_path, 'wb') as dat_file:
                                # 写入字符数量（4字节无符号整数）
                                count = len(chars_list)
                                dat_file.write(struct.pack('I', count))
                                
                                # 每个字符以UTF-32 LE编码写入（4字节）
                                for char in chars_list:
                                    char_bytes = char.encode('utf-32le')
                                    if len(char_bytes) == 4:
                                        dat_file.write(char_bytes)
                                    else:
                                        # 如果编码不是4字节，则使用替代方法
                                        dat_file.write(struct.pack('I', ord(char)))
                            
                            QMessageBox.information(self, "保存成功", f"图片已保存到：{file_path}\nIV版本对应的char_table.dat文件已保存至: {dat_path}\n原有的char_table.dat文件已备份为: {old_dat_path}")
                        except Exception as e:
                            QMessageBox.information(self, "保存成功", f"图片已保存到：{file_path}\n生成char_table.dat文件时出错: {e}")
                    else:
                        QMessageBox.information(self, "保存成功", f"图片已保存到：{file_path}\n已跳过生成char_table.dat文件")
                else:
                    # 检查是否应该有版本信息但丢失了
                    if char_positions and not (version and version in ["VC", "IV"]):
                        QMessageBox.information(self, "保存成功", f"图片已保存到：{file_path}\n注意：未能确定游戏版本，跳过生成.dat文件")
                    else:
                        QMessageBox.information(self, "保存成功", f"图片已保存到：{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"保存图片时出错：{e}")

def show_copyable_message(parent, title, text, icon=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setMinimumWidth(480)
    layout = QVBoxLayout(dlg)
    label = QLabel(title)
    label.setStyleSheet("font-weight:bold;font-size:15px;")
    layout.addWidget(label)
    edit = QTextEdit()
    edit.setReadOnly(True)
    edit.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
    edit.setText(text)
    edit.setStyleSheet("font-family: Consolas, 'Courier New', monospace; font-size: 13px;")
    layout.addWidget(edit)
    btn = QPushButton("关闭")
    btn.clicked.connect(dlg.accept)
    layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight)
    dlg.setModal(True)
    dlg.exec()

def show_info(parent, title, text):
    show_copyable_message(parent, title, text)

def show_warning(parent, title, text):
    show_copyable_message(parent, title, text)

def show_error(parent, title, text):
    show_copyable_message(parent, title, text)

class DebugMenu:
    def __init__(self, parent):
        self.parent = parent
        # 初始化版本和字符位置属性，用于在DebugMenuDialog关闭后仍可访问
        self.version = None
        self.char_positions = {}
        icons = {
            "char": QIcon.fromTheme("preferences-desktop-font"),
            "file": QIcon.fromTheme("document-open"),
            "settings": QIcon.fromTheme("preferences-system"),
            "help": QIcon.fromTheme("help-contents"),
            "gallery": QIcon.fromTheme("image-x-generic"),
        }
        self.actions = [
            {
                "name": "字符表单",
                "tip": "显示解析后的不重复非ASCII字符，按Unicode排序，每行64个字符。",
                "icon": icons["char"],
                "func": self.char_map_analysis,
            },
            {
                "name": "字库贴图",
                "tip": "将非ASCII字符生成4096x4096的图片，每行64个字符。",
                "icon": icons["file"],
                "func": self.generate_char_texture,
            },
            {
                "name": "码表编辑器",
                "tip": "编辑和管理码表文件，支持导入、导出和字符处理。",
                "icon": icons["settings"],
                "func": self.coding_table_editor,
            },
        ]

    def show_menu(self):
        dlg = DebugMenuDialog(self.parent, self.actions)
        dlg.setModal(False)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def parse_gxt_structure(self):
        """
        自动解析GXT文件结构，显示区块、偏移、长度、子表等详细信息。
        """
        path = getattr(self.parent, "gxt_file_path", None)
        if not path or not os.path.isfile(path):
            return "未检测到GXT文件。"
        try:
            with open(path, "rb") as f:
                data = f.read()
            info = []
            # 检查头部
            if data[:4] in (b'TABL', b'TKEY', b'GBL', b'\x04\x00\x08\x00'):
                offset = 0
                while offset < len(data):
                    tag = data[offset:offset+4]
                    if tag in (b'TABL', b'TKEY', b'TDAT'):
                        size = int.from_bytes(data[offset+4:offset+8], "little")
                        info.append(f"区块: {tag.decode(errors='ignore')} 偏移: 0x{offset:04X} 长度: {size} (0x{size:X})")
                        if tag == b'TABL':
                            # 解析TABL子表
                            tabl_count = size // 12
                            for i in range(tabl_count):
                                entry = data[offset+8+i*12:offset+8+(i+1)*12]
                                name = entry[:8].rstrip(b'\0').decode(errors='ignore')
                                tkey_off = int.from_bytes(entry[8:12], "little")
                                info.append(f"  子表: {name} TKEY偏移: 0x{tkey_off:04X}")
                        offset += 8 + size
                    elif tag == b'GBL':
                        info.append("检测到GTA2格式头部GBL")
                        offset += 6
                    elif tag[:2] == b'\x04\x00':
                        info.append("检测到SA/IV格式头部")
                        offset += 4
                    else:
                        # 跳过未知区块
                        offset += 4
                return "\n".join(info)
            else:
                return "无法识别的GXT文件头。"
        except Exception as e:
            return f"GXT结构解析失败: {e}"

    def hex_preview(self):
        """
        显示各区块的十六进制内容预览（前128字节），便于手动分析。
        """
        path = getattr(self.parent, "gxt_file_path", None)
        if not path or not os.path.isfile(path):
            return "未检测到GXT文件。"
        try:
            with open(path, "rb") as f:
                data = f.read()
            result = []
            offset = 0
            while offset < len(data):
                tag = data[offset:offset+4]
                if tag in (b'TABL', b'TKEY', b'TDAT'):
                    size = int.from_bytes(data[offset+4:offset+8], "little")
                    hexstr = data[offset:offset+min(size+8,128)].hex(" ").upper()
                    result.append(f"{tag.decode(errors='ignore')} @ 0x{offset:04X}:\n{hexstr}\n")
                    offset += 8 + size
                else:
                    offset += 4
            return "\n".join(result) if result else "未检测到标准区块。"
        except Exception as e:
            return f"十六进制预览失败: {e}"

    def token_analysis(self):
        """
        分析GXT文本中的Token（如~b~、~r~等）及其分布。
        """
        parsed = getattr(self.parent, "parsed_content", "")
        import re
        tokens = re.findall(r"~([a-zA-Z0-9_]+)~", parsed)
        from collections import Counter
        counter = Counter(tokens)
        if not counter:
            return "未检测到Token。"
        lines = ["Token分布统计："]
        for token, count in counter.most_common():
            lines.append(f"~{token}~ : {count} 次")
        return "\n".join(lines)

    def char_map_analysis(self):
        """
        显示解析后的不重复非ASCII字符，按Unicode排序，每行64个字符。
        """
        parsed = getattr(self.parent, "parsed_content", "")
        values = []
        for line in parsed.splitlines():
            if '=' in line:
                v = line.split('=', 1)[1]
                values.append(v)
        allchars = "".join(values)
        # 提取不重复的非ASCII字符
        unique_chars = sorted({c for c in allchars if ord(c) > 127}, key=ord)
        
        # 如果是IV版本，屏蔽指定字符
        iv_excluded_chars = {'', '©', '¬', '®', '·', 'È', 'É', 'à', 'á', 'ç', 'è', 'é', 'ñ', 'ú', 'ü', '', '', '', '', ' ', 'Á', 'ï'}
        # 从父对象获取GXT文件路径以检测版本
        gxt_file_path = getattr(self.parent, "gxt_file_path", None)
        if gxt_file_path and os.path.exists(gxt_file_path):
            # 尝试检测是否为IV版本
            try:
                with open(gxt_file_path, "rb") as f:
                    header = f.read(8)
                    # IV版本特征：前2字节为版本号4，接着2字节为16（表示16位字符）
                    if len(header) >= 4:
                        import struct
                        version, bits_per_char = struct.unpack('<HH', header[:4])
                        if version == 4 and bits_per_char == 16:
                            # 过滤IV版本特定字符
                            unique_chars = [c for c in unique_chars if c not in iv_excluded_chars]
            except Exception:
                # 如果检测失败，继续执行不过滤字符
                pass
        
        if not unique_chars:
            return "未检测到非ASCII字符。"
        # 每行64个字符
        lines = [f"总字符数: {len(unique_chars)}"]
        for i in range(0, len(unique_chars), 64):
            line = "".join(unique_chars[i:i+64])
            lines.append(line)
        return "\n".join(lines)

    def generate_char_texture(self):
        """
        生成字符贴图，将非ASCII字符绘制到4096x4096的画布上，每行64个字符。
        支持选择字体、粗体和斜体。
        """
        parsed = getattr(self.parent, "parsed_content", "")
        values = []
        for line in parsed.splitlines():
            if '=' in line:
                v = line.split('=', 1)[1]
                values.append(v)
        allchars = "".join(values)
        # 提取不重复的非ASCII字符
        unique_chars = sorted({c for c in allchars if ord(c) > 127}, key=ord)
        
        # 创建自定义字体选择对话框
        font_dialog = QDialog(self.parent)
        font_dialog.setWindowTitle("字体设置")
        font_dialog.resize(300, 300)  # 增加弹窗高度以容纳垂直偏移量输入框
        layout = QVBoxLayout(font_dialog)
        
        # 添加垂直偏移量输入框
        vertical_offset_layout = QHBoxLayout()
        vertical_offset_layout.setContentsMargins(0, 0, 0, 0)
        vertical_offset_layout.setSpacing(10)
        vertical_offset_label = QLabel("垂直偏移:")
        vertical_offset_label.setStyleSheet("font-family: 'Microsoft YaHei UI', 'Microsoft YaHei'; font-size: 13px; color: #2D3748;")
        vertical_offset_input = QSpinBox()
        vertical_offset_input.setRange(-100, 100)
        vertical_offset_input.setFixedWidth(100)
        vertical_offset_input.setStyleSheet("""
            QSpinBox {
                border: 2px solid #E2E8F0;
                border-radius: 10px;
                padding: 8px 12px;
                background: white;
                min-height: 20px;
                font-family: 'Microsoft YaHei UI', 'Microsoft YaHei';
                font-size: 13px;
                color: #2D3748;
            }
            QSpinBox:hover {
                border-color: #90CDF4;
            }
            QSpinBox:focus {
                border-color: #4299E1;
                background: #EBF8FF;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 24px;
                border-left: 2px solid #E2E8F0;
                subcontrol-origin: border;
                background: transparent;
            }
            QSpinBox::up-button {
                border-top-right-radius: 10px;
            }
            QSpinBox::down-button {
                border-bottom-right-radius: 10px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #EBF8FF;
            }
            QSpinBox::up-arrow, QSpinBox::down-arrow {
                width: 10px;
                height: 10px;
                image: none;
            }
            QSpinBox::up-arrow {
                subcontrol-origin: padding;
                subcontrol-position: center;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2D3748, stop:1 #2D3748);
                width: 6px;
                height: 2px;
                border-radius: 1px;
            }
            QSpinBox::down-arrow {
                subcontrol-origin: padding;
                subcontrol-position: center;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2D3748, stop:1 #2D3748);
                width: 6px;
                height: 2px;
                border-radius: 1px;
            }
        """)
        vertical_offset_layout.addWidget(vertical_offset_label)
        vertical_offset_layout.addWidget(vertical_offset_input)
        vertical_offset_layout.addStretch()
        # 根据版本设置默认值
        if hasattr(self.parent, 'version') and self.parent.version == "IV":
            vertical_offset_input.setValue(-4)  # IV版本默认向上偏移4像素
        else:
            vertical_offset_input.setValue(0)   # VC版本默认不偏移
        vertical_offset_layout.addWidget(vertical_offset_label)
        vertical_offset_layout.addWidget(vertical_offset_input)
        layout.addLayout(vertical_offset_layout)
        
        # 字体系列和样式选择（放在同一行）
        font_style_layout = QHBoxLayout()
        
        # 字体系列选择
        font_label = QLabel("选择字体:")
        font_combo = QComboBox()
        
        # 获取系统字体数据库（使用单例模式，遵循PyQt单例类使用规范）
        font_db = QFontDatabase
        families = font_db.families()
        for family in families:
            font_combo.addItem(family, family)
        
        font_combo.setCurrentText("Microsoft YaHei")
        
        # 字体样式选择
        style_label = QLabel("字体样式:")
        style_combo = QComboBox()
        
        # 添加到水平布局
        font_style_layout.addWidget(font_label)
        font_style_layout.addWidget(font_combo)
        font_style_layout.addWidget(style_label)
        font_style_layout.addWidget(style_combo)
        
        layout.addLayout(font_style_layout)
        
        # 字体大小选择（根据版本预设）- 隐藏此控件
        size_label = QLabel("字体大小:")
        size_label.setVisible(False)
        size_combo = QComboBox()
        size_combo.setVisible(False)
        
        # 粗体和斜体复选框（放在同一行）
        bold_italic_layout = QHBoxLayout()
        bold_italic_layout.addStretch()  # 添加弹簧使复选框靠右对齐
        
        # 粗体复选框
        bold_check = QCheckBox("仿粗体")
        bold_check.setChecked(False)
        
        # 斜体复选框
        italic_check = QCheckBox("斜体")
        italic_check.setVisible(False)
        
        # 添加到水平布局
        bold_italic_layout.addWidget(bold_check)
        bold_italic_layout.addWidget(italic_check)
        
        # 版本选择下拉栏
        version_label = QLabel("选择版本:")
        version_combo = QComboBox()
        version_combo.addItems(["VC", "IV"])
        version_combo.setCurrentText("VC")
        
        # 分辨率下拉栏
        resolution_label = QLabel("选择分辨率:")
        resolution_combo = QComboBox()
        resolution_combo.addItems(["4096x4096", "2048x2048", "1024x1024"])
        resolution_combo.setCurrentText("4096x4096")
        
        # 确认按钮
        confirm_btn = QPushButton("确认")
        confirm_btn.clicked.connect(font_dialog.accept)
        
        # 更新字体样式函数
        def update_styles():
            family = font_combo.currentData()
            style_combo.clear()
            if family:
                styles = font_db.styles(family)
                if styles:
                    for style in styles:
                        style_combo.addItem(style, style)
                    style_combo.setCurrentIndex(0)
                else:
                    style_combo.addItem("常规", "")
        
        # 根据版本更新字体大小函数
        def update_sizes():
            version = version_combo.currentText()
            size_combo.clear()
            # 根据版本设置预设字体大小
            if version == "III":
                size_combo.addItem("40", 40)
            elif version == "VC":
                size_combo.addItem("42", 42)
            elif version == "SA":
                size_combo.addItem("45", 45)
            elif version == "IV":
                size_combo.addItem("48", 48)
            size_combo.setCurrentIndex(0)
        
        # 连接信号
        font_combo.currentTextChanged.connect(update_styles)
        version_combo.currentTextChanged.connect(update_sizes)
        
        # 初始化样式和大小
        update_styles()
        update_sizes()
        
        # 添加控件到布局（不添加字体大小控件）
        # layout.addWidget(font_label)  # 已在水平布局中添加
        # layout.addWidget(font_combo)  # 已在水平布局中添加
        # layout.addWidget(style_label)  # 已在水平布局中添加
        # layout.addWidget(style_combo)  # 已在水平布局中添加
        # layout.addWidget(size_label)  # 隐藏此控件
        # layout.addWidget(size_combo)  # 隐藏此控件
        layout.addLayout(bold_italic_layout)  # 添加粗体和斜体的水平布局
        layout.addWidget(version_label)
        layout.addWidget(version_combo)
        layout.addWidget(resolution_label)
        layout.addWidget(resolution_combo)
        layout.addWidget(confirm_btn)
        
        # 显示对话框
        if font_dialog.exec() != QDialog.DialogCode.Accepted:
            return "操作已取消。"
            
        # 获取用户设置的垂直偏移量
        vertical_offset = vertical_offset_input.value()
        
        # 获取选中的字体设置
        font_family = font_combo.currentData()
        font_style = style_combo.currentData()
        font_size = size_combo.currentData()
        
        # 获取选中的版本
        selected_version = version_combo.currentText()
        
        # 如果是IV版本，屏蔽指定字符
        iv_excluded_chars = {'', '©', '¬', '®', '·', 'È', 'É', 'à', 'á', 'ç', 'è', 'é', 'ñ', 'ú', 'ü', '', '', '', '', ' ', 'Á', 'ï'}
        if selected_version == "IV":
            unique_chars = [c for c in unique_chars if c not in iv_excluded_chars]
        
        if not unique_chars:
            return "未检测到非ASCII字符。"

        # 创建字体
        font = QFont(font_family, font_size)
        if font_style:
            font.setStyleName(font_style)
        font.setBold(bold_check.isChecked())
        font.setItalic(italic_check.isChecked())
        font.setStyleStrategy(QFont.StyleStrategy.PreferQuality)
        
        # 解析分辨率
        resolution = resolution_combo.currentText()
        width, height = map(int, resolution.split('x'))
        
        # 创建4096x4096的画布（透明背景）
        pixmap = QPixmap(4096, 4096)
        pixmap.fill(Qt.GlobalColor.transparent)
        # 动态启用硬件加速或回退到软件渲染
        painter = QPainter(pixmap)
        if painter.isActive():
            device = painter.device()
            if device is not None and hasattr(device, 'paintingActive') and device.paintingActive():
                # 如果支持硬件加速
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
                painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering, True)
            else:
                # 回退到软件渲染
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        
        # 应用字体设置
        painter.setFont(font)
        # 设置画笔颜色为白色，不透明度为0.9
        painter.setPen(QColor(255, 255, 255, int(255 * 0.9)))

        # 计算每个字符的位置，边缘收缩2像素
        margin = 2
        chars_per_line = 64
        char_width = 4096 // chars_per_line
        # 根据版本设置行间距和字号大小
        version = version_combo.currentText()
        if version == "III":
            char_height = 80  # VC版本64 + 10
        elif version == "VC":
            char_height = 64
        elif version == "SA":
            char_height = 80
        elif version == "IV":
            char_height = 66
        x, y = 0, 0

        # 创建字符坐标映射表（用于生成.dat文件）
        char_positions = {}
        
        # 使用 QFontMetricsF 来获取更精确的字体度量信息
        font_metrics = QFontMetricsF(font)
        
        for char in unique_chars:
            # 计算字符的精确边界框
            bounding_rect = font_metrics.tightBoundingRect(char)
            
            # 计算字符在单元格中的垂直居中位置
            # 首先计算单元格的垂直中心
            cell_center_y = y + char_height / 2
            
            # 然后计算字符的基线位置，使其在单元格中垂直居中
            # ascent是从基线到字符顶部的距离，descent是从基线到字符底部的距离
            text_height = font_metrics.ascent() + font_metrics.descent()
            baseline_y = cell_center_y + (font_metrics.ascent() - text_height / 2) + vertical_offset  # 使用用户设置的垂直偏移量
            
            # 计算字符在单元格中的水平居中位置
            char_width_actual = font_metrics.horizontalAdvance(char)
            x_pos = x + (char_width - char_width_actual) / 2
            
            # 绘制字符，确保基线在网格正中间
            painter.drawText(int(x_pos), int(baseline_y), char)
            
            # 记录字符在贴图中的位置（行、列）
            row = y // char_height
            col = x // char_width
            char_positions[char] = (row, col)
            
            x += char_width
            if x >= 4096:
                x = 0
                y += char_height

        painter.end()
        
        # 压缩到用户选择的分辨率
        scaled_pixmap = pixmap.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        # 将 version 和 char_positions 传递给 DebugMenuDialog 实例
        # 使用更可靠的方法查找和设置属性
        dlg = None
        parent = self.parent
        if parent:
            dlg = parent.findChild(DebugMenuDialog)
        
        # 如果找到了DebugMenuDialog实例，则设置属性
        if dlg:
            dlg.version = version
            dlg.char_positions = char_positions
        else:
            # 如果没有找到DebugMenuDialog实例，将信息存储在DebugMenu中，供后续使用
            self.version = version
            self.char_positions = char_positions
        
        return "字符贴图生成完成。", [scaled_pixmap]

    def coding_table_editor(self):
        """
        码表编辑器功能，用于编辑和管理码表文件。
        """
        from PyQt6.QtWidgets import (
            QTableWidget, QTableWidgetItem, QHeaderView, QButtonGroup, 
            QRadioButton, QLineEdit, QGroupBox, QTextEdit, QHBoxLayout
        )
        from PyQt6.QtCore import Qt
        
        # 创建主部件
        widget = QWidget()
        layout = QHBoxLayout(widget)  # 主布局改为水平布局
        
        # 左侧区域 - 垂直布局放置两个功能框
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 创建字符输入区域
        char_input_group = QGroupBox("添加字符")
        char_input_layout = QVBoxLayout(char_input_group)
        
        # 字符输入框
        char_input_label = QLabel("输入字符（将自动去重）:")
        char_input_edit = QTextEdit()
        char_input_edit.setMaximumHeight(80)
        char_input_edit.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                font-family: 'Microsoft YaHei UI', 'Microsoft YaHei';
                font-size: 14px;
                color: #2D3748;
                padding: 8px;
            }
        """)
        
        # 排序选项
        sort_layout = QHBoxLayout()
        sort_label = QLabel("排序方式:")
        original_order_radio = QRadioButton("原始排序")
        unicode_order_radio = QRadioButton("Unicode排序")
        unicode_order_radio.setChecked(True)
        # 确保使用独立的单选框组
        sort_button_group = QButtonGroup()
        sort_button_group.addButton(original_order_radio)
        sort_button_group.addButton(unicode_order_radio)
        
        sort_layout.addWidget(sort_label)
        sort_layout.addWidget(original_order_radio)
        sort_layout.addWidget(unicode_order_radio)
        sort_layout.addStretch()
        
        # 添加字符按钮
        add_chars_button = QPushButton("填充字符")
        add_chars_button.clicked.connect(
            lambda: self._fill_characters(
                char_input_edit.toPlainText(), 
                table, 
                unicode_order_radio.isChecked()
            )
        )
        
        char_input_layout.addWidget(char_input_label)
        char_input_layout.addWidget(char_input_edit)
        char_input_layout.addLayout(sort_layout)
        char_input_layout.addWidget(add_chars_button)
        
        # 创建HEX填充区域
        hex_group = QGroupBox("HEX填充")
        hex_layout = QVBoxLayout(hex_group)
        
        # 起始HEX输入
        hex_input_layout = QHBoxLayout()
        hex_label = QLabel("起始HEX:")
        hex_input = QLineEdit()
        hex_input.setPlaceholderText("例如: 8b5c")
        hex_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #E2E8F0;
                border-radius: 10px;
                padding: 8px 12px;
                background: white;
                min-height: 20px;
                font-family: 'Microsoft YaHei UI', 'Microsoft YaHei';
                font-size: 14px;
                color: #2D3748;
            }
        """)
        
        hex_input_layout.addWidget(hex_label)
        hex_input_layout.addWidget(hex_input)
        
        # 跳过HEX输入
        skip_hex_layout = QHBoxLayout()
        skip_hex_label = QLabel("跳过HEX:")
        skip_hex_input = QLineEdit()
        skip_hex_input.setPlaceholderText("例如: 8b5c,8b5d")
        skip_hex_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #E2E8F0;
                border-radius: 10px;
                padding: 8px 12px;
                background: white;
                min-height: 20px;
                font-family: 'Microsoft YaHei UI', 'Microsoft YaHei';
                font-size: 14px;
                color: #2D3748;
            }
        """)
        
        skip_hex_layout.addWidget(skip_hex_label)
        skip_hex_layout.addWidget(skip_hex_input)
        
        # 排序选项
        hex_sort_layout = QHBoxLayout()
        hex_sort_label = QLabel("填充方向:")
        ascending_radio = QRadioButton("正序")
        descending_radio = QRadioButton("倒序")
        ascending_radio.setChecked(True)
        hex_sort_group = QButtonGroup()
        hex_sort_group.addButton(ascending_radio)
        hex_sort_group.addButton(descending_radio)
        
        hex_sort_layout.addWidget(hex_sort_label)
        hex_sort_layout.addWidget(ascending_radio)
        hex_sort_layout.addWidget(descending_radio)
        hex_sort_layout.addStretch()
        
        # HEX填充按钮
        hex_fill_button = QPushButton("HEX填充")
        hex_fill_button.clicked.connect(
            lambda: self._fill_hex_codes(
                table, 
                hex_input.text(), 
                skip_hex_input.text(),
                ascending_radio.isChecked()
            )
        )
        
        hex_layout.addLayout(hex_input_layout)
        hex_layout.addLayout(skip_hex_layout)
        hex_layout.addLayout(hex_sort_layout)
        hex_layout.addWidget(hex_fill_button)
        
        # 将两个功能框添加到左侧布局
        left_layout.addWidget(char_input_group)
        left_layout.addWidget(hex_group)
        left_layout.addStretch()  # 添加弹性空间
        
        # 右侧区域 - 表格和操作按钮
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        
        # 载入码表按钮
        load_button = QPushButton("载入码表")
        load_button.clicked.connect(lambda: self._load_coding_table(table))
        
        # 保存码表按钮
        save_button = QPushButton("保存码表")
        save_button.clicked.connect(lambda: self._save_coding_table(table))
        
        button_layout.addWidget(load_button)
        button_layout.addWidget(save_button)
        button_layout.addStretch()
        
        right_layout.addLayout(button_layout)
        
        # 创建表格
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["字符", "Unicode HEX"])
        header = table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        v_header = table.verticalHeader()
        if v_header:
            v_header.setVisible(False)
        table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                font-family: 'Microsoft YaHei UI', 'Microsoft YaHei';
                font-size: 14px;
                color: #2D3748;
                padding: 5px;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background: #F1F5F9;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        
        right_layout.addWidget(table)
        
        # 设置左右区域比例
        layout.addWidget(left_widget, 1)   # 左侧占1份
        layout.addWidget(right_widget, 3)  # 右侧占3份（表格区域更大）
        
        # 返回特殊标记，以便主界面正确处理
        return "码表编辑器界面", [widget]

    def _fill_characters(self, text, table, unicode_sorted):
        """
        填充字符到表格（舍弃原有内容，只保留排序方式）
        """
        from PyQt6.QtWidgets import QTableWidgetItem
        
        # 清空表格
        table.setRowCount(0)
        
        # 提取所有字符并去重
        chars = list(dict.fromkeys(text))  # 保持顺序的去重方法
        
        # 如果选择Unicode排序，则按Unicode排序
        if unicode_sorted:
            chars.sort()
            
        # 添加到表格
        for char in chars:
            if char.strip():  # 跳过空白字符
                row = table.rowCount()
                table.insertRow(row)
                table.setItem(row, 0, QTableWidgetItem(char))
                table.setItem(row, 1, QTableWidgetItem(""))  # HEX列留空，等待填写
                
    def _load_coding_table(self, table):
        """
        载入码表文件到表格
        """
        from PyQt6.QtWidgets import QTableWidgetItem
        
        file_path, _ = QFileDialog.getOpenFileName(
            table, "载入码表", "", "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # 清空表格
            table.setRowCount(0)
            
            # 解析并填充数据
            for line in lines:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    row = table.rowCount()
                    table.insertRow(row)
                    table.setItem(row, 0, QTableWidgetItem(parts[0]))
                    table.setItem(row, 1, QTableWidgetItem(parts[1]))
                    
        except Exception as error:
            QMessageBox.critical(table, "载入失败", f"载入码表时出错：{str(error)}")
            
    def _save_coding_table(self, table):
        """
        保存表格为码表文件
        """
        file_path, _ = QFileDialog.getSaveFileName(
            table, "保存码表", "", "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for row in range(table.rowCount()):
                    char_item = table.item(row, 0)
                    hex_item = table.item(row, 1)
                    
                    if char_item and hex_item:
                        char = char_item.text()
                        hex_code = hex_item.text()
                        if char and hex_code:  # 只保存非空行
                            f.write(f"{char}\t{hex_code}\n")
                            
            QMessageBox.information(table, "保存成功", f"码表已保存到：{file_path}")
        except Exception as error:
            QMessageBox.critical(table, "保存失败", f"保存码表时出错：{str(error)}")
            
    def _fill_hex_codes(self, table, start_hex, skip_hex, ascending):
        """
        为表格中的字符填充HEX编码（覆写模式）
        """
        from PyQt6.QtWidgets import QTableWidgetItem
        
        try:
            # 解析起始HEX
            start_value = int(start_hex, 16) if start_hex else 0
            
            # 解析跳过HEX值
            skip_values = set()
            if skip_hex:
                for hex_str in skip_hex.split(','):
                    hex_str = hex_str.strip()
                    if hex_str:
                        try:
                            skip_values.add(int(hex_str, 16))
                        except ValueError:
                            pass  # 忽略无效的HEX值
            
            # 确定步进方向
            step = 1 if ascending else -1
            
            # 填充HEX编码（覆写模式）
            current_value = start_value
            for row in range(table.rowCount()):
                # 跳过指定的HEX值
                while current_value in skip_values:
                    current_value += step
                
                # 设置当前HEX值
                item = QTableWidgetItem(format(current_value, '04x'))
                table.setItem(row, 1, item)
                current_value += step
                    
        except ValueError:
            QMessageBox.critical(table, "HEX错误", "起始HEX格式不正确")
        except Exception as error:
            QMessageBox.critical(table, "填充失败", f"HEX填充时出错：{str(error)}")
