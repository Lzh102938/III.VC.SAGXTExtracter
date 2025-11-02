import os
import requests
import tempfile
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QApplication, QDialog, QLabel
from PyQt6.QtCore import Qt

def convert_using_table(viewer):
    """修改为挂载码表功能"""
    try:
        # 检查是否已经挂载了码表
        if hasattr(viewer, 'mounted_table') and viewer.mounted_table:
            # 如果已挂载码表，则进行转换（正向或反向）
            if not hasattr(viewer, 'table_conversion_state'):
                viewer.table_conversion_state = 'original'  # original 或 converted
            
            if viewer.table_conversion_state == 'original':
                # 正向转换：码表字符转Unicode字符
                process_forward_conversion(viewer)
                viewer.table_conversion_state = 'converted'
                viewer.status_bar.findChild(QLabel, "status_message", Qt.FindChildOption.FindDirectChildrenOnly).setText("已完成正向转换（码表字符 -> Unicode）")
            else:
                # 反向转换：Unicode字符转码表字符
                process_reverse_conversion(viewer)
                viewer.table_conversion_state = 'original'
                viewer.status_bar.findChild(QLabel, "status_message", Qt.FindChildOption.FindDirectChildrenOnly).setText("已完成反向转换（Unicode -> 码表字符）")
        else:
            # 未挂载码表，选择并挂载码表
            from master.github_resources import GitHubResourceDialog
            github_dialog = GitHubResourceDialog(viewer)
            if github_dialog.exec() == QDialog.DialogCode.Accepted:
                resource = github_dialog.get_selected_resource()
                if resource == "local":
                    # 用户选择本地文件
                    file_path, _ = QFileDialog.getOpenFileName(viewer, viewer.tr("select_conversion_table"), "", "文本文件 (*.txt)")
                    if not file_path:
                        return
                    mount_conversion_table(viewer, file_path)
                elif resource and isinstance(resource, dict):
                    # 用户选择GitHub资源
                    try:
                        # 下载文件到临时文件
                        response = requests.get(resource['path'])
                        response.raise_for_status()
                        
                        # 创建临时文件
                        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8', suffix='.txt')
                        temp_file.write(response.text)
                        temp_file.close()
                        file_path = temp_file.name
                        
                        mount_conversion_table(viewer, file_path)
                        
                        # 清理临时文件
                        try:
                            os.unlink(temp_file.name)
                        except:
                            pass
                    except Exception as e:
                        QMessageBox.critical(viewer, viewer.tr("错误"), viewer.tr("从GitHub获取文件时出错: ") + str(e))
                else:
                    return  # 用户取消操作
            else:
                return  # 用户取消操作
    except ImportError as e:
        QMessageBox.critical(viewer, viewer.tr("错误"), viewer.tr("无法导入GitHub资源模块: ") + str(e))
        return


def mount_conversion_table(viewer, file_path):
    """挂载码表"""
    try:
        # 读取码表文件
        mapping = read_character_mapping(file_path)
        if mapping:
            viewer.mounted_table = mapping
            viewer.table_conversion_state = 'original'  # 重置转换状态
            table_name = os.path.basename(file_path)
            # 在状态栏显示消息
            status_label = viewer.status_bar.findChild(QLabel, "status_message", Qt.FindChildOption.FindDirectChildrenOnly)
            if status_label:
                status_label.setText(f"已挂载码表: {table_name}")
        else:
            QMessageBox.warning(viewer, viewer.tr("警告"), "码表文件格式不正确或为空")
    except Exception as e:
        QMessageBox.critical(viewer, viewer.tr("错误"), viewer.tr("挂载码表时出错: ") + str(e))


def read_character_mapping(file_path):
    """读取字符映射表"""
    mapping = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line:
                    parts = line.split('\t')
                    if len(parts) == 2:
                        chinese_char, replacement = parts
                        mapping[chinese_char] = swap_and_decode(replacement)
        return mapping
    except Exception as e:
        raise Exception(f"读取码表文件失败: {str(e)}")


def swap_and_decode(text):
    """将十六进制转为Unicode字符"""
    try:
        # 支持带或不带0x前缀的十六进制
        if text.startswith('0x') or text.startswith('0X'):
            hex_text = text[2:]  # 去掉0x前缀
        else:
            hex_text = text
        return chr(int(hex_text, 16))
    except ValueError:
        return text


def process_forward_conversion(viewer):
    """正向转换：码表字符转Unicode字符"""
    try:
        # 创建反向映射表（码表字符 -> Unicode字符）
        reverse_mapping = {v: k for k, v in viewer.mounted_table.items()}
        
        # 获取当前表格内容
        content_lines = []
        for row in range(viewer.output_table.rowCount()):
            key_item = viewer.output_table.item(row, 0)
            value_item = viewer.output_table.item(row, 1)
            
            if key_item and value_item:
                key = key_item.text()
                value = value_item.text()
                
                if key.startswith('[') and key.endswith(']'):
                    # Section行保持不变
                    content_lines.append(key)
                else:
                    # Value行进行正向转换（码表字符 -> Unicode字符）
                    converted_value = ""
                    for char in value:
                        # 先尝试直接匹配
                        if char in reverse_mapping:
                            converted_value += reverse_mapping[char]
                        else:
                            # 尝试十六进制小写格式匹配
                            hex_lower = f"{ord(char):04x}"
                            if hex_lower in reverse_mapping:
                                converted_value += reverse_mapping[hex_lower]
                            else:
                                # 尝试十六进制大写格式匹配
                                hex_upper = hex_lower.upper()
                                if hex_upper in reverse_mapping:
                                    converted_value += reverse_mapping[hex_upper]
                                else:
                                    # 如果都没有匹配，保留原字符
                                    converted_value += char
                    content_lines.append(f"{key}={converted_value}")
        
        # 更新表格显示
        content_str = "\n".join(content_lines)
        viewer.display_gxt_content_in_table(content_str)
        
        # 更新内部状态
        viewer.parsed_content = content_str
        
    except Exception as e:
        QMessageBox.critical(viewer, viewer.tr("错误"), viewer.tr("正向转换时出错: ") + str(e))


def process_reverse_conversion(viewer):
    """反向转换：Unicode字符转码表字符"""
    try:
        # 获取当前表格内容
        content_lines = []
        for row in range(viewer.output_table.rowCount()):
            key_item = viewer.output_table.item(row, 0)
            value_item = viewer.output_table.item(row, 1)
            
            if key_item and value_item:
                key = key_item.text()
                value = value_item.text()
                
                if key.startswith('[') and key.endswith(']'):
                    # Section行保持不变
                    content_lines.append(key)
                else:
                    # Value行进行反向转换（Unicode字符 -> 码表字符）
                    converted_value = ""
                    for char in value:
                        # 先尝试直接匹配
                        if char in viewer.mounted_table:
                            converted_value += viewer.mounted_table[char]
                        else:
                            # 尝试小写十六进制匹配
                            hex_lower = f"{ord(char):04x}"
                            if hex_lower in viewer.mounted_table:
                                converted_value += viewer.mounted_table[hex_lower]
                            else:
                                # 尝试大写十六进制匹配
                                hex_upper = hex_lower.upper()
                                if hex_upper in viewer.mounted_table:
                                    converted_value += viewer.mounted_table[hex_upper]
                                else:
                                    # 如果都没有匹配，保留原字符
                                    converted_value += char
                    content_lines.append(f"{key}={converted_value}")
        
        # 更新表格显示
        content_str = "\n".join(content_lines)
        viewer.display_gxt_content_in_table(content_str)
        
        # 更新内部状态
        viewer.parsed_content = content_str
        
    except Exception as e:
        QMessageBox.critical(viewer, viewer.tr("错误"), viewer.tr("反向转换时出错: ") + str(e))