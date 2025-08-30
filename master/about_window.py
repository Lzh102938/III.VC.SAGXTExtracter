from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QScrollArea, QPushButton, QFrame, QWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QIcon, QColor, QFontDatabase

def open_about_window(parent):
    about_text = parent.tr("about_text_html")
    about_dialog = QDialog(parent, Qt.WindowType.FramelessWindowHint)
    about_dialog.setWindowTitle(parent.tr("about_window_title"))
    about_dialog.setWindowIcon(QIcon('./favicon.ico'))
    
    # 加载系统字体
    font_family = "Segoe UI" if "Segoe UI" in QFontDatabase.families() else "Microsoft YaHei UI"
    font = QFont(font_family, 10)
    about_dialog.setFont(font)
    
    # 应用现代化样式表
    about_dialog.setStyleSheet("""
        QDialog {
            background: #F8FAFC;
            border-radius: 10px;
            border: 1px solid #E2E8F0;
        }
        QScrollArea {
            background: transparent;
            border: none;
        }
        QLabel {
            color: #2D3748;
            font-size: 14px;
            padding: 10px 15px;
            line-height: 1.5;
            font-family: 'Microsoft YaHei UI';
        }
        QScrollBar:vertical {
            background: #F1F5F9;
            width: 10px;
            margin: 2px 0 2px 0;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical {
            background: #BFD7ED;
            min-height: 30px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background: #7BA7D7;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
    """)

    # 主布局 - 更紧凑
    main_layout = QVBoxLayout(about_dialog)
    main_layout.setContentsMargins(8, 8, 8, 8)
    main_layout.setSpacing(4)
    
    # 滚动区域
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QFrame.Shape.NoFrame)
    
    # 关于文本容器
    text_container = QWidget()
    text_layout = QVBoxLayout(text_container)
    text_layout.setContentsMargins(0, 0, 0, 0)
    
    # 关于文本
    about_label = QLabel(about_text)
    about_label.setTextFormat(Qt.TextFormat.RichText)
    about_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
    about_label.setWordWrap(True)
    about_label.setFont(font)
    text_layout.addWidget(about_label)
    
    scroll_area.setWidget(text_container)
    
    # 分隔线
    separator = QFrame()
    separator.setFrameShape(QFrame.Shape.HLine)
    separator.setStyleSheet("color: #E5E7EB;")
    
    # 关闭按钮
    close_button = QPushButton(parent.tr("close_button_text"))
    close_button.clicked.connect(about_dialog.accept)
    close_button.setStyleSheet("""
        QPushButton {
            border: 2px solid gray;
            border-radius: 10px;
            padding: 5px;
            min-width: 80px;
            background: #FFFFFF;
            color: #2c2c2c;
        }
        QPushButton:hover {
            background: #E2E8F0;
        }
    """)
    
    # 添加到布局
    main_layout.addWidget(scroll_area)
    main_layout.addWidget(separator)
    main_layout.addWidget(close_button, 0, Qt.AlignmentFlag.AlignRight)
    
    # 窗口尺寸 - 更紧凑
    about_dialog.resize(600, 450)
    
    # 添加淡入动画
    fade_in = QPropertyAnimation(about_dialog, b"windowOpacity")
    fade_in.setDuration(200)
    fade_in.setStartValue(0)
    fade_in.setEndValue(1)
    fade_in.setEasingCurve(QEasingCurve.Type.OutQuad)
    fade_in.start()
    
    # 居中显示
    screen = about_dialog.screen()
    if screen is not None:
        screen_geometry = screen.availableGeometry()
        x = (screen_geometry.width() - about_dialog.width()) // 2
        y = (screen_geometry.height() - about_dialog.height()) // 2
        about_dialog.move(x, y)
    
    about_dialog.exec()