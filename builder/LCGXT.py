import re
import struct
import os

class LCGXT:
    SIZE_OF_TKEY = 12
    
    def __init__(self):
        self.m_GxtData = {}
        self.m_WideCharCollection = set()
    
    def load_text(self, path):
        self.m_GxtData = {}
        self.m_WideCharCollection = set()
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.rstrip('\n')
                    # 跳过空行和注释
                    if not line or line.startswith(';'):
                        continue
                    
                    # 使用正则匹配键值对
                    match = re.match(r'([0-9a-zA-Z_]{1,7})=(.*)', line)
                    if not match:
                        print(f"Invalid line:\n{line}\n")
                        return False
                    
                    key = match.group(1)
                    value = match.group(2)
                    utf16_data = self.utf8_to_utf16(value)
                    
                    # 特殊键名处理
                    if key in ["CHS2500", "CHS3000"] or key not in self.m_GxtData:
                        self.m_GxtData[key] = utf16_data
                        # 收集宽字符
                        for char in utf16_data:
                            if char >= 0x80:
                                self.m_WideCharCollection.add(char)
        except Exception as e:
            print(f"Error reading file: {e}")
            return False
        
        return True
    
    def save_as_gxt(self, path):
        if not self.m_GxtData:
            return
        
        # 计算块大小
        key_block_size = len(self.m_GxtData) * self.SIZE_OF_TKEY
        data_block_size = self.get_data_block_size()
        
        try:
            with open(path, 'wb') as f:
                # 写入TKEY头部
                f.write(b'TKEY')
                f.write(struct.pack('<I', key_block_size))
                
                # 写入TDAT头部占位
                f.seek(8 + key_block_size)
                f.write(b'TDAT')
                f.write(struct.pack('<I', data_block_size))
                
                # 写入键值数据
                data_start_pos = 8 + key_block_size + 8
                current_data_pos = data_start_pos
                
                for key, utf16_data in self.m_GxtData.items():
                    # 写入TKEY条目
                    offset = current_data_pos - (key_block_size + 16)
                    key_name = key.ljust(7, '\x00')[:7].encode('ascii')
                    
                    f.seek(8 + (list(self.m_GxtData.keys()).index(key) * self.SIZE_OF_TKEY))
                    f.write(struct.pack('<I', offset))
                    f.write(key_name + b'\x00')
                    
                    # 写入字符串数据
                    f.seek(current_data_pos)
                    for char in utf16_data:
                        f.write(struct.pack('<H', char))
                    current_data_pos += len(utf16_data) * 2
        except Exception as e:
            print(f"Error writing GXT file: {e}")
    
    def get_data_block_size(self):
        size = 0
        for utf16_data in self.m_GxtData.values():
            size += len(utf16_data) * 2
        return size
    
    def generate_wmhhz_stuff(self):
        try:
            # 写入CHARACTERS.txt
            with open('CHARACTERS.txt', 'wb') as f:
                f.write(b'\xFF\xFE')  # UTF-16 LE BOM
                row = 0
                col = 0
                for char in sorted(self.m_WideCharCollection):
                    f.write(struct.pack('<H', char))
                    col += 1
                    if col >= 64:
                        f.write(b'\x0A\x00')  # UTF-16 LE换行
                        row += 1
                        col = 0
            
            # 写入TABLE.txt
            with open('TABLE.txt', 'w', encoding='utf-8') as f:
                row = 0
                col = 0
                for char in sorted(self.m_WideCharCollection):
                    f.write(f"m_Table[0x{char:04X}] = {{{row},{col}}};\n")
                    col += 1
                    if col >= 64:
                        row += 1
                        col = 0
        except Exception as e:
            print(f"Error generating files: {e}")
    
    @staticmethod
    def utf8_to_utf16(s):
        """将UTF-8字符串转换为UTF-16 LE码点列表，包含结尾空字符"""
        utf16_bytes = s.encode('utf-16le')
        utf16_list = [char for char in struct.unpack(f'<{len(utf16_bytes)//2}H', utf16_bytes)]
        utf16_list.append(0)  # 添加结尾空字符
        return utf16_list

# 主程序
if __name__ == "__main__":
    temp = LCGXT()
    if temp.load_text("GTA3.txt"):
        temp.save_as_gxt("wm_lcchs.gxt")
        temp.generate_wmhhz_stuff()