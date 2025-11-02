#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import os
import tempfile
import webbrowser
from typing import List, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, 
    QListWidgetItem, QLabel, QProgressDialog, QMessageBox, QFrame,
    QSizePolicy, QApplication, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap, QColor, QPalette

# GitHub 仓库信息
GITHUB_API_URL = "https://api.github.com/repos/GTASA-ACCHS/CN.resource/contents"
GITHUB_REPO_URL = "https://github.com/GTASA-ACCHS/CN.resource"

class ResourceLoader(QThread):
    """在后台线程中加载GitHub资源"""
    resources_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def run(self):
        try:
            response = requests.get(GITHUB_API_URL)
            response.raise_for_status()
            data = response.json()
            
            # 过滤支持的文件类型（.txt 和 .md），排除 README.md，并且只保留文件名包含"码表"的文件
            supported_files = [
                item for item in data 
                if (item['name'].endswith('.txt') or item['name'].endswith('.md')) 
                and item['name'].lower() != 'readme.md'
                and '码表' in item['name']
            ]
            
            # 处理文件数据
            resources_data = []
            for index, item in enumerate(supported_files):
                # 格式化文件大小
                size = item['size']
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size // 1024} KB"
                else:
                    size_str = f"{size // (1024 * 1024)} MB"
                
                # 根据文件扩展名确定类型
                file_type = "Markdown" if item['name'].endswith('.md') else "文档"
                description = "Markdown 文档" if file_type == "Markdown" else "汉化资源文件"
                
                resources_data.append({
                    "id": index,
                    "name": item['name'],
                    "path": item['download_url'],
                    "type": file_type,
                    "size": size_str,
                    "rawSize": size,
                    "description": description
                })
            
            self.resources_loaded.emit(resources_data)
        except requests.RequestException as e:
            self.error_occurred.emit(str(e))
        except Exception as e:
            self.error_occurred.emit(str(e))


class GitHubResourceDialog(QDialog):
    """GitHub资源选择对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.resources_data = []
        self.selected_resource = None
        self.init_ui()
        self.load_resources()
        
    def init_ui(self):
        self.setWindowTitle("选择GitHub资源")
        self.setMinimumSize(700, 400)
        self.resize(800, 500)
        
        # 设置窗口样式，与主界面保持一致
        self.setStyleSheet("""
            QDialog {
                background: #F8FAFC;
                font-family: "Microsoft YaHei UI";
            }
            QTableWidget {
                background: white;
                color: #2D3748;
                border: 1px solid #E2E8F0;
                border-radius: 5px;
                gridline-color: #E2E8F0;
                selection-background-color: #CBD5E0;
                selection-color: #2D3748;
            }
            QTableWidget::item {
                padding: 6px;
            }
            QTableWidget::item:selected {
                background-color: #E2E8F0;
            }
            QHeaderView::section {
                background-color: #F1F5F9;
                color: #4A5568;
                padding: 8px;
                border: 1px solid #E2E8F0;
                font-weight: bold;
            }
            QPushButton {
                border: 1px solid #CBD5E0;
                border-radius: 6px;
                padding: 6px 12px;
                background: #FFFFFF;
                color: #2c2c2c;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #F1F5F9;
            }
            QPushButton:pressed {
                background: #E2E8F0;
            }
            QPushButton:disabled {
                color: #A0AEC0;
                background: #F7FAFC;
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 标题
        title_label = QLabel("GitHub 码表资源")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #1a202c;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 5px;
            }
        """)
        main_layout.addWidget(title_label)
        
        # 描述
        desc_label = QLabel("从以下资源中选择一个码表文件，或使用本地文件")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("""
            QLabel {
                color: #718096;
                font-size: 12px;
                margin-bottom: 10px;
            }
        """)
        main_layout.addWidget(desc_label)
        
        # 资源表格
        self.resource_table = QTableWidget()
        self.resource_table.setColumnCount(4)
        self.resource_table.setHorizontalHeaderLabels(["文件名", "类型", "大小", "描述"])
        self.resource_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.resource_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.resource_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.resource_table.setAlternatingRowColors(True)
        
        # 设置列宽策略
        header = self.resource_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            
        self.resource_table.setColumnWidth(1, 80)
        self.resource_table.setColumnWidth(2, 80)
        
        # 隐藏垂直表头
        vertical_header = self.resource_table.verticalHeader()
        if vertical_header:
            vertical_header.setVisible(False)
            
        self.resource_table.itemClicked.connect(self.on_item_clicked)
        self.resource_table.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        main_layout.addWidget(self.resource_table)
        
        # 链接区域
        link_label = QLabel('<a href="http://tool.bmpchs.asia/">访问静态资源站</a>')
        link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        link_label.setStyleSheet("""
            QLabel {
                color: #3182ce;
                font-size: 11px;
                margin: 5px 0;
            }
        """)
        link_label.setOpenExternalLinks(True)
        main_layout.addWidget(link_label)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.local_button = QPushButton("📁 本地选择")
        self.local_button.clicked.connect(self.select_local)
        button_layout.addWidget(self.local_button)
        
        self.refresh_button = QPushButton("🔄 刷新")
        self.refresh_button.clicked.connect(self.load_resources)
        button_layout.addWidget(self.refresh_button)
        
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.select_button = QPushButton("选择")
        self.select_button.clicked.connect(self.accept)
        self.select_button.setEnabled(False)
        button_layout.addWidget(self.select_button)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        
    def load_resources(self):
        """加载GitHub资源"""
        self.resource_table.setRowCount(0)
        self.select_button.setEnabled(False)
        
        # 显示进度对话框
        self.progress_dialog = QProgressDialog("正在加载资源...", "取消", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setWindowTitle("请稍候")
        self.progress_dialog.show()
        
        # 启动后台线程加载资源
        self.loader_thread = ResourceLoader()
        self.loader_thread.resources_loaded.connect(self.on_resources_loaded)
        self.loader_thread.error_occurred.connect(self.on_load_error)
        self.loader_thread.start()
        
    def on_resources_loaded(self, resources_data):
        """资源加载完成"""
        self.progress_dialog.close()
        self.resources_data = resources_data
        
        if not resources_data:
            QMessageBox.information(self, "提示", "未找到任何资源")
            return
            
        # 填充资源表格
        self.resource_table.setRowCount(len(resources_data))
        for row, resource in enumerate(resources_data):
            # 文件名
            name_item = QTableWidgetItem(resource['name'])
            name_item.setData(Qt.ItemDataRole.UserRole, resource)  # type: ignore
            self.resource_table.setItem(row, 0, name_item)
            
            # 类型
            type_item = QTableWidgetItem(resource['type'])
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.resource_table.setItem(row, 1, type_item)
            
            # 大小
            size_item = QTableWidgetItem(resource['size'])
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.resource_table.setItem(row, 2, size_item)
            
            # 描述
            desc_item = QTableWidgetItem(resource['description'])
            self.resource_table.setItem(row, 3, desc_item)
            
        self.resource_table.resizeRowsToContents()
            
    def on_load_error(self, error_msg):
        """加载资源出错"""
        self.progress_dialog.close()
        QMessageBox.critical(self, "错误", f"加载资源时出错: {error_msg}")
        
    def on_item_clicked(self, item):
        """单击项目时启用选择按钮"""
        self.select_button.setEnabled(True)
        
    def on_item_double_clicked(self, item):
        """双击项目选择"""
        row = item.row()
        resource_item = self.resource_table.item(row, 0)
        if resource_item:
            self.selected_resource = resource_item.data(Qt.ItemDataRole.UserRole)  # type: ignore
            self.accept()
        
    def select_local(self):
        """选择本地文件"""
        self.selected_resource = "local"
        self.accept()
        
    def accept(self):
        """确认选择"""
        current_item = self.resource_table.currentItem()
        if current_item and not self.selected_resource:
            row = current_item.row()
            resource_item = self.resource_table.item(row, 0)
            if resource_item:
                self.selected_resource = resource_item.data(Qt.ItemDataRole.UserRole)  # type: ignore
        elif not self.selected_resource:
            QMessageBox.warning(self, "警告", "请选择一个资源文件或使用本地文件")
            return
            
        super().accept()
        
    def get_selected_resource(self):
        """获取选中的资源"""
        return self.selected_resource


def fetch_resources() -> List[Dict]:
    """
    从 GitHub 仓库获取资源数据
    
    Returns:
        List[Dict]: 资源数据列表
    """
    try:
        response = requests.get(GITHUB_API_URL)
        response.raise_for_status()
        data = response.json()
        
        # 过滤支持的文件类型（.txt 和 .md），排除 README.md，并且只保留文件名包含"码表"的文件
        supported_files = [
            item for item in data 
            if (item['name'].endswith('.txt') or item['name'].endswith('.md')) 
            and item['name'].lower() != 'readme.md'
            and '码表' in item['name']
        ]
        
        # 处理文件数据
        resources_data = []
        for index, item in enumerate(supported_files):
            # 格式化文件大小
            size = item['size']
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size // 1024} KB"
            else:
                size_str = f"{size // (1024 * 1024)} MB"
            
            # 根据文件扩展名确定类型
            file_type = "Markdown" if item['name'].endswith('.md') else "文档"
            description = "Markdown 文档" if file_type == "Markdown" else "汉化资源文件"
            
            resources_data.append({
                "id": index,
                "name": item['name'],
                "path": item['download_url'],
                "type": file_type,
                "size": size_str,
                "rawSize": size,
                "description": description
            })
        
        return resources_data
    
    except requests.RequestException as e:
        print(f"获取资源时出错: {e}")
        # 返回空列表而不是默认数据
        return []


def export_to_json(resources_data: List[Dict], filename: str = "gtasa_resources.json") -> None:
    """
    将资源数据导出为 JSON 文件
    
    Args:
        resources_data (List[Dict]): 资源数据列表
        filename (str): 导出文件名
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(resources_data, f, ensure_ascii=False, indent=2)
        print(f"资源数据已成功导出到 {filename}")
    except Exception as e:
        print(f"导出 JSON 文件时出错: {e}")


def main():
    """
    主函数
    """
    print("正在获取资源数据...")
    resources_data = fetch_resources()
    
    if not resources_data:
        print("未找到任何资源")
        # 仍然导出空的 JSON 文件
        export_to_json(resources_data)
        return
    
    print(f"共找到 {len(resources_data)} 个资源")
    for resource in resources_data:
        print(f"- {resource['name']} ({resource['type']}, {resource['size']})")
    
    # 导出 JSON 文件
    export_to_json(resources_data)
    print("操作完成!")


if __name__ == "__main__":
    main()