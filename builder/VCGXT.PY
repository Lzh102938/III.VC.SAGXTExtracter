#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import os
import struct
import sys
from collections import OrderedDict
from functools import cmp_to_key

class VCGXT:
    SizeOfTABL = 12
    SizeOfTKEY = 12

    def __init__(self):
        self.m_WideCharCollection = set()
        self.m_GxtData = OrderedDict()

    def _table_sort_method(self, lhs, rhs):
        """自定义表排序逻辑：MAIN表优先"""
        if rhs == "MAIN":
            return False
        if lhs == "MAIN":
            return True
        return lhs < rhs

    def _skip_utf8_signature(self, file):
        """跳过UTF-8 BOM"""
        start_pos = file.tell()
        header = file.read(3)
        if header != b'\xef\xbb\xbf':
            file.seek(start_pos)
        return file

    def _utf8_to_utf16(self, s):
        """UTF-8转UTF-16LE并返回整数列表"""
        try:
            encoded = s.encode('utf-16le')
            return [struct.unpack('<H', encoded[i:i+2])[0] 
                    for i in range(0, len(encoded), 2)] + [0]
        except UnicodeEncodeError:
            print(f"编码错误: {s}")
            return []

    def LoadText(self, path):
        """加载并解析GXT文本文件"""
        self.m_GxtData.clear()
        current_table = None
        
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"打开文件失败: {e}")
            return False

        table_format = re.compile(r'^\[([0-9A-Z_]{1,7})\]$')
        entry_format = re.compile(r'^([0-9A-Z_]{1,7})=(.*)$')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith(';'):
                continue

            # 匹配表头
            table_match = table_format.match(line)
            if table_match:
                table_name = table_match.group(1)
                current_table = table_name
                if table_name not in self.m_GxtData:
                    self.m_GxtData[table_name] = {}
                continue

            # 匹配键值对
            entry_match = entry_format.match(line)
            if entry_match:
                if current_table is None:
                    print(f"第{line_num}行: 键不属于任何表")
                    return False
                    
                key = entry_match.group(1)
                value = entry_match.group(2)
                
                # 检查波浪号配对
                if value.count('~') % 2 != 0:
                    print(f"第{line_num}行: 无效的波浪号格式 - {key}")
                    continue
                
                # 转换编码并存储
                utf16_data = self._utf8_to_utf16(value)
                if key in self.m_GxtData[current_table]:
                    print(f"第{line_num}行: 重复的键 - {key}")
                    return False
                    
                self.m_GxtData[current_table][key] = utf16_data
                
                # 收集宽字符
                for char in utf16_data:
                    if char > 0x7F:
                        self.m_WideCharCollection.add(char)
                continue

            print(f"第{line_num}行: 无效格式 - {line}")
            return False

        # 应用自定义排序
        self.m_GxtData = OrderedDict(sorted(
            self.m_GxtData.items(), 
            key=cmp_to_key(lambda a, b: -1 if self._table_sort_method(a[0], b[0]) else 1)
        ))
        return True

    def SaveAsGXT(self, path):
        """保存为GXT二进制文件"""
        try:
            with open(path, 'wb') as f:
                # 写入TABL头部
                f.write(b'TABL')
                table_block_size = len(self.m_GxtData) * self.SizeOfTABL
                f.write(struct.pack('<I', table_block_size))
                
                # 预留TABL块空间
                table_offsets = {}
                f.seek(8 + table_block_size, 0)
                
                # 处理每个表
                for table_name, entries in self.m_GxtData.items():
                    # 记录当前表位置
                    table_offsets[table_name] = f.tell()
                    
                    # 写入TKEY头部
                    key_block_size = len(entries) * self.SizeOfTKEY
                    if table_name != "MAIN":
                        f.write(table_name.ljust(8, '\x00').encode('ascii'))
                    f.write(b'TKEY')
                    f.write(struct.pack('<I', key_block_size))
                    
                    # 预留TKEY条目空间
                    key_entries_pos = f.tell()
                    f.seek(key_block_size, 1)
                    
                    # 写入TDAT头部
                    data_block_size = sum(len(v) * 2 for v in entries.values())
                    f.write(b'TDAT')
                    f.write(struct.pack('<I', data_block_size))
                    tdat_start = f.tell()
                    
                    # 写入字符串数据并记录偏移
                    key_offsets = []
                    for key, data in entries.items():
                        offset = f.tell() - tdat_start
                        key_offsets.append((key, offset))
                        f.write(struct.pack(f'<{len(data)}H', *data))
                    
                    # 回填TKEY条目
                    f.seek(key_entries_pos)
                    for key, offset in key_offsets:
                        f.write(struct.pack('<I', offset))
                        f.write(key.ljust(8, '\x00').encode('ascii'))
                    f.seek(0, 2)  # 回到文件末尾
                
                # 回填TABL条目
                f.seek(8)
                for table_name in self.m_GxtData:
                    f.write(table_name.ljust(8, '\x00').encode('ascii'))
                    f.write(struct.pack('<I', table_offsets[table_name]))
                    
            print(f"成功生成: {path}")
            return True
                
        except Exception as e:
            print(f"保存GXT失败: {e}")
            return False

    def GenerateWMHHZStuff(self):
        """生成字符映射文件"""
        try:
            # 生成CHARACTERS.txt
            with open('CHARACTERS.txt', 'wb') as f:
                f.write(b'\xFF\xFE')  # UTF-16LE BOM
                
                # 按行列组织字符
                char_table = {}
                sorted_chars = sorted(self.m_WideCharCollection)
                for idx, char in enumerate(sorted_chars):
                    row = idx // 64
                    col = idx % 64
                    char_table[char] = (row, col)
                    f.write(struct.pack('<H', char))
                    if col == 63:
                        f.write(b'\x0A\x00')  # 换行符
                
            # 生成wm_vcchs.dat
            with open('wm_vcchs.dat', 'wb') as f:
                # 初始化65536个默认值(?字符)
                default_entry = struct.pack('BB', 63, 63)
                for _ in range(0x10000):
                    f.write(default_entry)
                
                # 更新实际字符位置
                for char, (row, col) in char_table.items():
                    if char < 0x10000:
                        f.seek(char * 2)
                        f.write(struct.pack('BB', row, col))
            
            print("成功生成WMHHZ文件")
            return True
            
        except Exception as e:
            print(f"生成WMHHZ文件失败: {e}")
            return False

if __name__ == "__main__":
    # 使用示例
    builder = VCGXT()
    
    if builder.LoadText("GTAVC.txt"):
        builder.SaveAsGXT("wm_vcchs.gxt")
        builder.GenerateWMHHZStuff()
    else:
        print("加载文本文件失败")