from PyQt6.QtWidgets import QDialog, QVBoxLayout, QScrollArea, QPushButton, QFrame, QWidget, QLabel, QHBoxLayout, QLCDNumber, QMessageBox
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QTimer, QRect, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QColor, QFontDatabase, QTextDocument, QMouseEvent, QPainter, QBrush, QPen
from PyQt6.QtWidgets import QTextBrowser

def open_about_window(parent):
    about_text = parent.tr("about_text_html")
    about_dialog = QDialog(parent, Qt.WindowType.FramelessWindowHint)
    about_dialog.setWindowTitle(parent.tr("about_window_title"))
    about_dialog.setWindowIcon(QIcon('./favicon.ico'))
    
    # 添加点击计数器属性
    setattr(about_dialog, 'click_count', 0)
    setattr(about_dialog, 'egg_triggered', False)
    
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
        QTextBrowser {
            background: transparent;
            color: #2D3748;
            font-size: 14px;
            padding: 10px 15px;
            line-height: 1.5;
            font-family: "Microsoft YaHei UI";
            border: none;
        }
        /* 滚动条样式使用全局统一样式 */
    """)

    # 主布局 - 更紧凑
    main_layout = QVBoxLayout(about_dialog)
    main_layout.setContentsMargins(8, 8, 8, 8)
    main_layout.setSpacing(4)
    
    # 滚动区域
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QFrame.Shape.NoFrame)
    
    # 使用 QTextBrowser 替代 QLabel 以支持更全面的 HTML
    text_browser = QTextBrowser()
    text_browser.setOpenExternalLinks(True)
    text_browser.setFrameStyle(QFrame.Shape.NoFrame)
    
    # 创建 QTextDocument 并设置 HTML 内容
    doc = QTextDocument()
    # 设置默认CSS样式表
    default_css = '''
        body { 
            color: #2D3748; 
            font-family: "Microsoft YaHei UI"; 
            font-size: 14px; 
            line-height: 1.5; 
        }
        h1, h2, h3, h4, h5, h6 { 
            color: #1a202c; 
            font-weight: bold; 
            margin-top: 20px; 
            margin-bottom: 10px; 
        }
        h1 { font-size: 24px; }
        h2 { font-size: 20px; }
        h3 { font-size: 18px; }
        h4 { font-size: 16px; }
        p { 
            margin-top: 0; 
            margin-bottom: 10px; 
        }
        a { 
            color: #3182ce; 
            text-decoration: none; 
        }
        a:hover { 
            text-decoration: underline; 
        }
        code { 
            background-color: #f7fafc; 
            padding: 2px 4px; 
            border-radius: 3px; 
            font-family: "Consolas", "Courier New", monospace; 
        }
        pre { 
            background-color: #f7fafc; 
            padding: 10px; 
            border-radius: 5px; 
            overflow-x: auto; 
        }
        pre code { 
            background-color: transparent; 
            padding: 0; 
        }
        ul, ol { 
            margin-top: 0; 
            margin-bottom: 10px; 
            padding-left: 20px; 
        }
        li { 
            margin-bottom: 5px; 
        }
        table { 
            border-collapse: collapse; 
            width: 100%; 
            margin-bottom: 10px; 
        }
        th, td { 
            border: 1px solid #e2e8f0; 
            padding: 8px; 
            text-align: left; 
        }
        th { 
            background-color: #f7fafc; 
            font-weight: bold; 
        }
        blockquote { 
            border-left: 4px solid #e2e8f0; 
            padding: 0 15px; 
            margin: 0 0 10px 0; 
            color: #718096; 
        }
    '''
    doc.setDefaultStyleSheet(default_css)
    doc.setHtml(about_text)
    text_browser.setDocument(doc)
    
    scroll_area.setWidget(text_browser)
    
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
    
    # 添加鼠标点击事件处理
    def handle_click(a0: QMouseEvent | None):
        # 如果彩蛋已经触发，则不再处理点击
        if getattr(about_dialog, 'egg_triggered', False):
            return
            
        # 增加点击计数
        click_count = getattr(about_dialog, 'click_count', 0) + 1
        setattr(about_dialog, 'click_count', click_count)
        
        # 当点击达到7次时触发彩蛋
        if click_count >= 7:
            trigger_easter_egg(about_dialog, parent)
    
    # 安装事件过滤器来捕获点击事件
    about_dialog.mousePressEvent = handle_click
    
    # 居中显示
    screen = about_dialog.screen()
    if screen is not None:
        screen_geometry = screen.availableGeometry()
        x = (screen_geometry.width() - about_dialog.width()) // 2
        y = (screen_geometry.height() - about_dialog.height()) // 2
        about_dialog.move(x, y)
    
    # 添加弹出动画
    def show_with_animation():
        # 初始化透明度和缩放
        about_dialog.setWindowOpacity(0.0)
        about_dialog.resize(600, 450)  # 确保尺寸正确
        
        # 淡入动画
        fade_in = QPropertyAnimation(about_dialog, b"windowOpacity")
        fade_in.setDuration(200)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # 缩放动画
        scale_animation = QPropertyAnimation(about_dialog, b"size")
        scale_animation.setDuration(300)
        scale_animation.setStartValue(about_dialog.size() * 0.8)
        scale_animation.setEndValue(about_dialog.size())
        scale_animation.setEasingCurve(QEasingCurve.Type.OutBack)
        
        # 启动动画
        fade_in.start()
        scale_animation.start()
        
        # 保存动画引用以防止被垃圾回收
        setattr(about_dialog, 'fade_in', fade_in)
        setattr(about_dialog, 'scale_animation', scale_animation)
    
    # 延迟显示动画以确保窗口已正确初始化
    QTimer.singleShot(0, show_with_animation)
    
    about_dialog.exec()

class SnakeGame(QWidget):
    # 定义分数变化信号
    score_changed = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.setFixedSize(380, 280)
        
        # 游戏参数
        self.square_size = 20
        self.game_speed = 300  # 毫秒
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_game)
        
        # 游戏状态
        self.is_paused = False
        self.game_started = False
        
        # 贪吃蛇初始位置
        self.snake = [QPoint(5, 5), QPoint(4, 5), QPoint(3, 5)]
        self.direction = Qt.Key.Key_Right
        self.next_direction = Qt.Key.Key_Right
        
        # 食物位置
        self.food = QPoint(10, 10)
        self.generate_food()
        
        # 分数
        self.score = 0
        
        # 设置键盘焦点
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.setPen(QPen(QColor(0, 0, 0)))
        painter.drawRect(0, 0, self.width(), self.height())
        
        # 绘制贪吃蛇
        painter.setBrush(QBrush(QColor(0, 255, 0)))  # 绿色蛇身
        painter.setPen(QPen(QColor(0, 200, 0)))
        for segment in self.snake:
            painter.drawRect(
                segment.x() * self.square_size,
                segment.y() * self.square_size,
                self.square_size,
                self.square_size
            )
        
        # 绘制蛇头（用不同颜色）
        painter.setBrush(QBrush(QColor(0, 200, 0)))  # 深绿色蛇头
        painter.setPen(QPen(QColor(0, 150, 0)))
        head = self.snake[0]
        painter.drawRect(
            head.x() * self.square_size,
            head.y() * self.square_size,
            self.square_size,
            self.square_size
        )
        
        # 绘制食物
        painter.setBrush(QBrush(QColor(255, 0, 0)))  # 红色食物
        painter.setPen(QPen(QColor(200, 0, 0)))
        painter.drawEllipse(
            self.food.x() * self.square_size,
            self.food.y() * self.square_size,
            self.square_size,
            self.square_size
        )
        
        # 如果游戏暂停，显示暂停文字 (使用十六进制表示"暂停")
        if self.is_paused and self.game_started:
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            # "\u6682\u505c" 是 "暂停" 的十六进制表示
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "\u6682\u505c")
    
    def keyPressEvent(self, event):
        key = event.key()
        
        # 控制方向，防止反向移动
        if key == Qt.Key.Key_Left and self.direction != Qt.Key.Key_Right:
            self.next_direction = Qt.Key.Key_Left
        elif key == Qt.Key.Key_Right and self.direction != Qt.Key.Key_Left:
            self.next_direction = Qt.Key.Key_Right
        elif key == Qt.Key.Key_Up and self.direction != Qt.Key.Key_Down:
            self.next_direction = Qt.Key.Key_Up
        elif key == Qt.Key.Key_Down and self.direction != Qt.Key.Key_Up:
            self.next_direction = Qt.Key.Key_Down
        elif key == Qt.Key.Key_Space:
            self.toggle_pause()
        
        super().keyPressEvent(event)
    
    def update_game(self):
        if self.is_paused:
            return
            
        # 更新方向
        self.direction = self.next_direction
        
        # 保存蛇尾位置，用于可能的增长
        tail = self.snake[-1]
        
        # 移动蛇头
        head = self.snake[0]
        if self.direction == Qt.Key.Key_Left:
            new_head = QPoint(head.x() - 1, head.y())
        elif self.direction == Qt.Key.Key_Right:
            new_head = QPoint(head.x() + 1, head.y())
        elif self.direction == Qt.Key.Key_Up:
            new_head = QPoint(head.x(), head.y() - 1)
        elif self.direction == Qt.Key.Key_Down:
            new_head = QPoint(head.x(), head.y() + 1)
        
        # 检查是否撞墙
        if (new_head.x() < 0 or new_head.x() >= self.width() // self.square_size or
            new_head.y() < 0 or new_head.y() >= self.height() // self.square_size):
            self.game_over()
            return
        
        # 检查是否撞到自己
        if new_head in self.snake:
            self.game_over()
            return
        
        # 将新头添加到蛇身
        self.snake.insert(0, new_head)
        
        # 检查是否吃到食物
        if new_head == self.food:
            # 增加分数
            self.score += 10
            self.score_changed.emit(self.score)
            
            # 生成新食物
            self.generate_food()
            
            # 加快游戏速度
            if self.game_speed > 100:
                self.game_speed -= 5
                self.timer.setInterval(self.game_speed)
        else:
            # 移除蛇尾
            self.snake.pop()
        
        # 更新显示
        self.update()
    
    def generate_food(self):
        import random
        while True:
            x = random.randint(0, self.width() // self.square_size - 1)
            y = random.randint(0, self.height() // self.square_size - 1)
            self.food = QPoint(x, y)
            
            # 确保食物不在蛇身上
            if self.food not in self.snake:
                break
    
    def start_game(self):
        if not self.game_started:
            self.game_started = True
            self.timer.start(self.game_speed)
        elif self.is_paused:
            self.is_paused = False
            self.timer.start(self.game_speed)
        self.update()
    
    def toggle_pause(self):
        if not self.game_started:
            return
            
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.timer.stop()
        else:
            self.timer.start(self.game_speed)
        self.update()
    
    def restart_game(self):
        # 重置游戏状态
        self.snake = [QPoint(5, 5), QPoint(4, 5), QPoint(3, 5)]
        self.direction = Qt.Key.Key_Right
        self.next_direction = Qt.Key.Key_Right
        self.score = 0
        self.game_speed = 300
        self.is_paused = False
        self.game_started = False
        
        self.score_changed.emit(self.score)
        self.generate_food()
        self.timer.setInterval(self.game_speed)
        self.timer.stop()
        self.update()
    
    def game_over(self):
        self.timer.stop()
        self.game_started = False
        
        # 在游戏区域显示游戏结束文字
        self.update()
        
        # 用对话框显示游戏结束信息
        from PyQt6.QtWidgets import QMessageBox
        # 使用十六进制表示"游戏结束"
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("\u6e38\u620f\u7ed3\u675f")
        # 使用十六进制表示"游戏结束!\n最终得分: "
        msg_box.setText(f"\u6e38\u620f\u7ed3\u675f!\n\u6700\u7ec8\u5f97\u5206: {self.score}")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()

def trigger_easter_egg(dialog, parent):
    """触发彩蛋函数"""
    # 设置彩蛋已触发标志
    setattr(dialog, 'egg_triggered', True)
    
    # 创建贪吃蛇游戏对话框
    # 使用十六进制表示"贪吃蛇小游戏"
    game_dialog = QDialog(dialog)
    game_dialog.setWindowTitle("\u8d2a\u5403\u86c7\u5c0f\u6e38\u620f")
    game_dialog.setWindowIcon(QIcon('./favicon.ico'))
    game_dialog.resize(400, 400)
    game_dialog.setFixedSize(400, 400)
    
    # 设置样式
    game_dialog.setStyleSheet("""
        QDialog {
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #87CEEB, stop: 1 #98FB98);
            border-radius: 10px;
        }
        QLabel {
            color: #2c2c2c;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton {
            background-color: #4CAF50;
            border: none;
            color: white;
            padding: 8px 16px;
            text-align: center;
            text-decoration: none;
            font-size: 14px;
            margin: 2px;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QLCDNumber {
            background-color: black;
            color: #00FF00;
            border-radius: 5px;
        }
    """)
    
    # 创建主布局
    main_layout = QVBoxLayout(game_dialog)
    main_layout.setContentsMargins(10, 10, 10, 10)
    
    # 创建标题
    # 使用十六进制表示"彩蛋"
    title_label = QLabel("\u5f69\u86cb")
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    # 创建分数显示
    score_layout = QHBoxLayout()
    # 使用十六进制表示"得分:"
    score_label = QLabel("\u5f97\u5206:")
    score_display = QLCDNumber()
    score_display.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
    score_display.display(0)
    score_layout.addWidget(score_label)
    score_layout.addWidget(score_display)
    
    # 创建游戏区域
    game_area = SnakeGame()
    game_area.setStyleSheet("background-color: #000000; border-radius: 5px;")
    
    # 创建控制按钮
    # 使用十六进制表示按钮文本
    start_button = QPushButton("\u5f00\u59cb\u6e38\u620f")      # 开始游戏
    pause_button = QPushButton("\u6682\u505c")                   # 暂停
    restart_button = QPushButton("\u91cd\u65b0\u5f00\u59cb")     # 重新开始
    close_button = QPushButton("\u5173\u95ed\u6e38\u620f")       # 关闭游戏
    
    # 连接按钮功能
    start_button.clicked.connect(game_area.start_game)
    pause_button.clicked.connect(game_area.toggle_pause)
    restart_button.clicked.connect(game_area.restart_game)
    close_button.clicked.connect(game_dialog.accept)
    
    # 添加按钮到布局
    button_layout = QHBoxLayout()
    button_layout.addWidget(start_button)
    button_layout.addWidget(pause_button)
    button_layout.addWidget(restart_button)
    button_layout.addWidget(close_button)
    
    # 添加所有组件到主布局
    main_layout.addWidget(title_label)
    main_layout.addLayout(score_layout)
    main_layout.addWidget(game_area)
    main_layout.addLayout(button_layout)
    
    # 连接分数更新信号
    game_area.score_changed.connect(score_display.display)
    
    # 显示对话框
    game_dialog.exec()
    
    # 修改主窗口标题显示发现彩蛋
    # 使用十六进制表示"彩蛋已触发"
    dialog.setWindowTitle(parent.tr("\u5f69\u86cb\u5df2\u89e6\u53d1"))
