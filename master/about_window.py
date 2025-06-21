from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt

def open_about_window(parent):
    about_text = parent.tr("about_text_html")
    about_dialog = QDialog(parent)
    about_dialog.setWindowTitle(parent.tr("about_window_title"))
    about_dialog.setStyleSheet("""
        QDialog {
            background: #F8FAFC;
        }
        QScrollArea {
            background: transparent;
            border: none;
        }
        QLabel {
            color: #2D3748;
            font-size: 14px;
            font-family: 'Microsoft YaHei UI', 'Microsoft YaHei';
        }
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
    """)

    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)

    about_label = QLabel(about_text)
    about_label.setTextFormat(Qt.TextFormat.RichText)
    about_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
    about_label.setWordWrap(True)
    scroll_area.setWidget(about_label)

    layout = QVBoxLayout(about_dialog)
    layout.addWidget(scroll_area)
    about_dialog.setLayout(layout)

    about_dialog.resize(660, 650)
    about_dialog.setSizeGripEnabled(True)

    # 获取屏幕大小，兼容PyQt6
    screen = about_dialog.screen()
    if screen is not None:
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        if about_dialog.width() > screen_width or about_dialog.height() > screen_height:
            desired_width = min(about_dialog.width(), screen_width - 100)
            desired_height = min(about_dialog.height(), screen_height - 100)
            about_dialog.resize(desired_width, desired_height)

    about_dialog.exec()
