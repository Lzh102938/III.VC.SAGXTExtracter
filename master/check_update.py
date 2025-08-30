# master/check_update.py
from PyQt6.QtCore import QObject, pyqtSignal, QUrl
from PyQt6.QtNetwork import QNetworkRequest, QNetworkAccessManager, QNetworkReply
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
        self.fallback_url = "https://raw.githubusercontent.com/Lzh102938/III.VC.SAGXTExtracter/refs/heads/main/update.json"
        self.using_fallback = False

    def check(self):
        """发起更新检查请求"""
        url = QUrl("http://bmpchs.asia/gxtviewer/update/update.json")
        request = QNetworkRequest(url)
        self.using_fallback = False
        self.manager.get(request)

    def check_fallback(self):
        """发起备用更新检查请求"""
        url = QUrl(self.fallback_url)
        request = QNetworkRequest(url)
        self.using_fallback = True
        self.manager.get(request)

    def handle_response(self, reply):
        try:
            err = reply.error()
            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            status = int(status) if status is not None else None

            # 优先处理网络错误
            if err != QNetworkReply.NetworkError.NoError:
                # 如果主更新源失败且还未尝试备用源，则尝试备用源
                if not self.using_fallback:
                    self.check_fallback()
                    return
                else:
                    self.error_occurred.emit(reply.errorString())
                    return

            if status != 200:
                # 如果主更新源失败且还未尝试备用源，则尝试备用源
                if not self.using_fallback:
                    self.check_fallback()
                    return
                else:
                    self.error_occurred.emit(f"HTTP 错误，状态码：{status}")
                    return

            raw = reply.readAll().data().decode('utf-8')
            info = json.loads(raw)
            remote_version = info.get('version')
            release_url    = info.get('release_url')
            message        = info.get('message', '')

            if remote_version and release_url and self.is_newer_version(remote_version):
                self.update_available.emit(remote_version, release_url, message)

        except Exception as e:
            # 如果主更新源失败且还未尝试备用源，则尝试备用源
            if not self.using_fallback:
                self.check_fallback()
                return
            else:
                self.error_occurred.emit(f"更新检查内部异常：{e}")

        finally:
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