from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGroupBox, QFileDialog,
    QMessageBox, QTableWidget, QTableWidgetItem, QLineEdit, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

class ClickableLabel(QLabel):
    clicked = QtCore.pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()

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
