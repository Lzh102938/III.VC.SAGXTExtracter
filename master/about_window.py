from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QScrollArea, QDesktopWidget
from PyQt5.QtCore import Qt

def open_about_window(parent):
    about_text = parent.tr("about_text_html")
    
    # Create a QDialog for more flexibility
    about_dialog = QDialog(parent)
    about_dialog.setWindowTitle(parent.tr("about_window_title"))
    
    # Create a scroll area to hold the label
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)  # Allow the label to resize with the scroll area

    # Create a label to display the text
    about_label = QLabel(about_text)
    about_label.setTextFormat(Qt.RichText)
    about_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
    about_label.setWordWrap(True)  # Enable word wrap for better content fitting
    scroll_area.setWidget(about_label)

    # Create a layout and add the scroll area
    layout = QVBoxLayout(about_dialog)
    layout.addWidget(scroll_area)
    about_dialog.setLayout(layout)
    
    # Set the default size to 660x650
    about_dialog.resize(660, 650)
    
    # Make the dialog resizable
    about_dialog.setSizeGripEnabled(True)

    # Get the available screen size
    screen = QDesktopWidget().availableGeometry()
    screen_width = screen.width()
    screen_height = screen.height()

    # Ensure the dialog doesn't exceed screen size
    if about_dialog.width() > screen_width or about_dialog.height() > screen_height:
        desired_width = min(about_dialog.width(), screen_width - 100)
        desired_height = min(about_dialog.height(), screen_height - 100)
        about_dialog.resize(desired_width, desired_height)
    
    # Show the dialog
    about_dialog.exec_()
