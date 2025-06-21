import os
import collections
import io
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QWidget, QSizePolicy, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap

class DebugMenuDialog(QDialog):
    def __init__(self, parent, actions):
        super().__init__(parent)
        self.setWindowTitle("GXT专业调试菜单")
        # 修正 PyQt6 WindowType 写法
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setMinimumSize(900, 600)
        self.resize(900, 600)
        self.actions = actions
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # 左侧菜单
        self.menu_list = QListWidget()
        self.menu_list.setMinimumWidth(220)
        self.menu_list.setMaximumWidth(320)
        self.menu_list.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        for action in self.actions:
            item = QListWidgetItem(action["icon"], action["name"])
            item.setToolTip(action.get("tip", ""))
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
        self.text_edit.setReadOnly(True)
        self.text_edit.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.text_edit.setStyleSheet("font-family: Consolas, 'Courier New', monospace; font-size: 13px;")
        self.text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.content_layout.addWidget(self.text_edit)
        splitter.addWidget(self.content_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([240, 660])

        # 关闭按钮
        btn = QPushButton("关闭")
        btn.clicked.connect(self.accept)
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.content_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.menu_list.currentRowChanged.connect(self._on_menu_changed)
        self._on_menu_changed(0)

    def _on_menu_changed(self, idx):
        if idx < 0 or idx >= len(self.actions):
            return
        action = self.actions[idx]
        self.title_label.setText(action["name"])
        try:
            result = action["func"]()
            if isinstance(result, tuple) and len(result) == 2:
                content, pixmaps = result
                self.text_edit.setText(content if content else "(无内容)")
                # 清除旧图
                for i in reversed(range(self.content_layout.count())):
                    widget = self.content_layout.itemAt(i).widget()
                    if isinstance(widget, QLabel) and widget != self.title_label:
                        self.content_layout.removeWidget(widget)
                        widget.deleteLater()
                # 添加新图
                for pix in pixmaps:
                    img_label = QLabel()
                    img_label.setPixmap(pix)
                    img_label.setAlignment(Qt.AlignCenter)
                    self.content_layout.insertWidget(self.content_layout.count()-2, img_label)
            else:
                self.text_edit.setText(result if result else "(无内容)")
        except Exception as e:
            self.text_edit.setText(f"发生异常: {e}")

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
        icons = {
            "parse": QIcon.fromTheme("document-open"),
            "hex": QIcon.fromTheme("accessories-text-editor"),
            "token": QIcon.fromTheme("applications-graphics"),
            "char": QIcon.fromTheme("preferences-desktop-font"),
            "tutorial": QIcon.fromTheme("help-browser"),
        }
        self.actions = [
            {
                "name": "GXT结构解析",
                "tip": "自动解析GXT文件结构，显示区块、偏移、长度、子表等详细信息。",
                "icon": icons["parse"],
                "func": self.parse_gxt_structure,
            },
            {
                "name": "区块与十六进制预览",
                "tip": "显示各区块的十六进制内容预览，便于手动分析。",
                "icon": icons["hex"],
                "func": self.hex_preview,
            },
            {
                "name": "Token与控制符分析",
                "tip": "分析GXT文本中的Token（如~b~、~r~等）及其分布。",
                "icon": icons["token"],
                "func": self.token_analysis,
            },
            {
                "name": "字符映射与编码",
                "tip": "分析GXT Value的编码、字符分布、特殊符号映射。",
                "icon": icons["char"],
                "func": self.char_map_analysis,
            },
            {
                "name": "GXT格式入门教程",
                "tip": "简明教程：如何手动分析、解密、提取和修改GXT文本。",
                "icon": icons["tutorial"],
                "func": self.gxt_tutorial,
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
        分析GXT Value的编码、字符分布、特殊符号映射。
        """
        parsed = getattr(self.parent, "parsed_content", "")
        import collections
        import re
        values = []
        for line in parsed.splitlines():
            if '=' in line:
                v = line.split('=', 1)[1]
                values.append(v)
        allchars = "".join(values)
        char_counter = collections.Counter(allchars)
        lines = ["字符分布统计（前20）："]
        for ch, cnt in char_counter.most_common(20):
            if ord(ch) < 32:
                disp = f"\\x{ord(ch):02X}"
            else:
                disp = ch
            lines.append(f"{disp} : {cnt} 次")
        # 检查常见特殊符号
        specials = [c for c in allchars if ord(c) >= 0x7B]
        if specials:
            lines.append(f"\n高位特殊符号（如心形/护甲/星星等）数量: {len(specials)}")
        return "\n".join(lines)

    def gxt_tutorial(self):
        return (
"""【GXT格式详解与实用教程】

一、GXT是什么？
------------------------
GXT是GTA系列游戏的“文本字典”文件，负责将游戏中的Key（如"GM_OVR"）映射为实际显示的文本（如"Game Over"），支持多语言切换和文本批量替换。

二、GXT文件结构基础
------------------------
1. 常见区块
- TABL：子表目录（VC/SA等有，III无）
- TKEY：Key索引表，存储Key名或CRC32及其在TDAT的偏移
- TDAT：Value数据区，存储所有字符串内容
- 头部：部分版本有，包含版本号、编码等

2. 各代差异
- GTA2/III：无TABL，TKEY直接跟TDAT，Key为明文
- VC/LCS/VCS：有TABL，支持多子表，TKEY为明文
- SA/IV：TKEY为CRC32，TDAT可能加密，编码多为1252或自定义表

三、手动分析GXT的步骤
------------------------
1. 用HxD等十六进制编辑器打开GXT文件。
2. 查找"TABL"、"TKEY"、"TDAT"等区块标记，记录偏移和长度。
3. TABL区块（如有）列出所有子表及其TKEY偏移。
4. TKEY区块存储Key（或CRC32）和TDAT偏移。
5. TDAT区块存储所有字符串内容，通常以0结尾。

四、如何提取和修改文本
------------------------
1. 解析TKEY，获取所有Key及其在TDAT的偏移。
2. 跳转到TDAT区块，读取对应偏移的字符串（遇到0结束）。
3. 如TDAT内容为乱码，尝试每字节异或0xAA解密（SA部分版本）。
4. 修改文本后注意保持区块长度、偏移、编码一致，否则游戏可能崩溃。

五、编码与加密说明
------------------------
- III/VC多为UTF-16LE或ASCII，SA为Windows-1252，IV为自定义表。
- SA部分GXT加密，需异或0xAA解密。
- SA/IV等版本TKEY为CRC32，需用工具或脚本计算Key的CRC32。

六、Token与特殊符号
------------------------
- ~b~ ~r~ ~g~等为颜色/控制符，~PED_FIREWEAPON~等为按钮图标。
- 字符映射表详见Wiki，部分高位字符为心形、护甲、星星等特殊符号。
- Token需成对出现，否则可能导致游戏崩溃。

七、实用举例
------------------------
1. **定位区块**：在HxD中Ctrl+F查找"TKEY"，记下偏移，再查找"TDAT"。
2. **提取Key-Value**：TKEY每项通常12字节（偏移+Key名），用偏移定位TDAT字符串。
3. **解密SA TDAT**：导出TDAT区块，用Python脚本`bytes([b^0xAA for b in data])`批量解密。
4. **CRC32计算**：用Python的`binascii.crc32(key.encode('ascii'))`获得Key的CRC32。

八、推荐工具与资源
------------------------
- HxD、010 Editor（十六进制分析）
- SannyBuilder、GXT Editor、OpenIV（可视化编辑）
- Python脚本（批量提取/转换/CRC32计算）
- GTAMods Wiki（https://gtamods.com/wiki/GXT）

九、常见问题与排查
------------------------
- 乱码/不可读：多为TDAT加密或编码不符，需尝试解密和多种编码
- Key找不到Value：TKEY偏移错误或CRC32算法不符
- 区块长度/偏移异常：文件损坏或版本不兼容
- 修改后崩溃：区块长度、偏移、编码未同步

十、进阶建议
------------------------
- 多用区块结构、偏移、编码、Token等多维度交叉验证。
- 修改后建议用本工具的“结构解析”“十六进制预览”功能自检。
- 参考Wiki和社区资料，结合实际文件多做实验。

【结语】
GXT分析并不难，关键是理解区块结构和编码/加密方式。多用工具、脚本和社区资源，遇到问题多查文档和示例，逐步掌握即可。
"""
        )
