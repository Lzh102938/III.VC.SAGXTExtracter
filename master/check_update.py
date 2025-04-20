# master/check_update.py
from PyQt5.QtCore import QObject, pyqtSignal, QUrl
from PyQt5.QtNetwork import QNetworkRequest, QNetworkReply, QNetworkAccessManager
import json
import re

class UpdateChecker(QObject):
    update_available = pyqtSignal(str, str, str)  # 新版本号, 发布链接, 升级说明
    error_occurred = pyqtSignal(str)         # 信号：错误信息

    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version
        self.manager = QNetworkAccessManager(self)  # 关键！必须设置父对象
        self.manager.finished.connect(self.handle_response)

    def check(self):
        """发起更新检查请求"""
        url = QUrl("https://raw.githubusercontent.com/Lzh102938/III.VC.SAGXTExtracter/refs/heads/main/update.json")
        request = QNetworkRequest(url)
        self.manager.get(request)

    def handle_response(self, reply):
        """处理网络响应，获取 HTTP 状态码并根据情况发射信号"""
        try:
            # 1. 获取网络层错误枚举
            err = reply.error()
            # 2. 获取 HTTP 状态码并转换为 int（可能为 None）
            status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
            status = int(status) if status is not None else None

            print(f"收到响应，HTTP 状态码：{status}，网络错误枚举：{err}")

            # 3. 网络错误，优先上报
            if err != QNetworkReply.NoError:
                self.error_occurred.emit(reply.errorString())
                return

            # 4. HTTP 状态码非 200 时上报
            if status != 200:
                self.error_occurred.emit(f"HTTP 错误，状态码：{status}")
                return

            # 5. 读取并解析 JSON
            raw = reply.readAll().data().decode('utf-8')
            info = json.loads(raw)
            remote_version = info.get('version')
            release_url    = info.get('release_url')
            message        = info.get('message', '')

            # 6. 对比版本，若有新版本则发射更新信号
            if remote_version and release_url and self.is_newer_version(remote_version):
                self.update_available.emit(remote_version, release_url, message)

        except Exception as e:
            # 捕获一切异常，避免未处理错误闪退
            self.error_occurred.emit(f"更新检查内部异常：{e}")

        finally:
            # 确保 reply 对象正确销毁
            reply.deleteLater()

    def is_newer_version(self, remote_version):
        """比较版本号"""
        try:
            # 过滤非数字字符
            remote_clean = re.sub(r'[^\d.]', '', remote_version)
            current_clean = re.sub(r'[^\d.]', '', self.current_version)
            
            remote = list(map(int, remote_clean.split('.')))
            current = list(map(int, current_clean.split('.')))
            
            # 补齐版本号长度
            max_len = max(len(remote), len(current))
            remote += [0]*(max_len - len(remote))
            current += [0]*(max_len - len(current))
            
            return remote > current
        except Exception as e:
            print(f"版本比较错误: {str(e)}")
            return False
