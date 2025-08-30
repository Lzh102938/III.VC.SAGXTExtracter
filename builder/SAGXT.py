import os
import re
import struct

class SAGXT:
    SizeOfTABL = 12
    SizeOfTKEY = 8

    def __init__(self):
        self.m_GxtData = dict()  # 表名 -> {hash: 文本}
        self.m_WideCharCollection = set()

    def load_text(self, path: str) -> bool:
        table_format = re.compile(r"\[([0-9A-Z_]{1,7})\]")
        entry_format = re.compile(r"([0-9a-fA-F]{1,8})=(.+)")

        current_table = None
        self.m_GxtData.clear()
        self.m_WideCharCollection.clear()

        try:
            with open(path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(';'):
                        continue

                    table_match = table_format.fullmatch(line)
                    entry_match = entry_format.fullmatch(line)

                    if table_match:
                        table_name = table_match.group(1)
                        self.m_GxtData[table_name] = dict()
                        current_table = self.m_GxtData[table_name]
                    elif entry_match:
                        if current_table is None:
                            print(f"键 {entry_match.group(1)} 没有对应表。")
                            return False

                        hash_key = int(entry_match.group(1), 16)
                        text = entry_match.group(2)

                        if hash_key in current_table:
                            print(f"重复项:\n{entry_match.group(1)}\n所在表:\n{table_name}\n")
                            return False

                        current_table[hash_key] = text
                        for ch in text:
                            self.m_WideCharCollection.add(ch)
                    else:
                        print(f"非法行:\n{line}\n")
                        return False
            return True
        except Exception as e:
            print(f"读取文件出错: {e}")
            return False

    def save_as_gxt(self, path: str):
        try:
            with open(path, 'wb') as f:
                f.write(b"\x04\x00\x08\x00")
                f.write(b"TABL")
                table_block_size = len(self.m_GxtData) * self.SizeOfTABL
                f.write(struct.pack('<I', table_block_size))

                fo_table_block = 12
                fo_key_block = 12 + table_block_size
                key_block_offset = fo_key_block

                for table_name, entries in sorted(self.m_GxtData.items(), key=self._table_sort):
                    key_block_size = len(entries) * self.SizeOfTKEY
                    data_block_size = self._get_data_block_size(entries)

                    # 写入 TABL
                    f.seek(fo_table_block)
                    name_bytes = table_name.encode('ascii')[:7].ljust(8, b'\x00')
                    f.write(name_bytes)
                    f.write(struct.pack('<I', key_block_offset))
                    fo_table_block += self.SizeOfTABL

                    # 写入 TKEY header
                    f.seek(fo_key_block)
                    if table_name != "MAIN":
                        f.write(name_bytes)
                    f.write(b"TKEY")
                    f.write(struct.pack('<I', key_block_size))
                    fo_key_block = f.tell()
                    f.seek(key_block_size, 1)

                    # 写入 TDAT header
                    tdat_offset = f.tell()
                    f.write(b"TDAT")
                    f.write(struct.pack('<I', data_block_size))
                    fo_data_block = f.tell()

                    # 写入 TKEY 和 TDAT 实际数据
                    for hash_key, value in entries.items():
                        data_offset = fo_data_block - tdat_offset - 8
                        f.seek(fo_key_block)
                        f.write(struct.pack('<II', data_offset, hash_key))
                        fo_key_block += self.SizeOfTKEY
                        f.seek(fo_data_block)
                        f.write(value.encode('utf-8') + b'\x00')
                        fo_data_block = f.tell()

                    fo_key_block = f.tell()
                    key_block_offset = fo_key_block
        except Exception as e:
            print(f"写入GXT失败: {e}")

    def generate_wmhhz_stuff(self):
        try:
            with open("TABLE.txt", "w", encoding='utf-8') as conv_code, \
                open("CHARACTERS.txt", "wb") as characters_set:

                characters_set.write(b"\xFF\xFE")  # UTF-16LE BOM

                row, column = 0, 0
                for char in sorted(self.m_WideCharCollection):
                    if ord(char) <= 0x7F:
                        continue  # 跳过 ASCII

                    conv_code.write(f"m_Table[0x{ord(char):X}] = {{{row},{column}}};\n")
                    characters_set.write(char.encode('utf-16le'))

                    if column < 63:
                        column += 1
                    else:
                        row += 1
                        characters_set.write('\n'.encode('utf-16le'))
                        column = 0
        except Exception as e:
            print(f"生成 WMHHZ 输出失败: {e}")


    def _get_data_block_size(self, table: dict) -> int:
        return sum(len(v.encode('utf-8')) + 1 for v in table.values())

    def _table_sort(self, item):
        return (item[0] != 'MAIN', item[0])  # MAIN优先，其它按字典序


if __name__ == "__main__":
    sagxt = SAGXT()
    if sagxt.load_text("GTASA.txt"):
        sagxt.save_as_gxt("wm_sachs.gxt")
        sagxt.generate_wmhhz_stuff()
        print("构建完成。")
    else:
        print("加载失败。")
