import re
import struct

def generate_gxt(input_file, output_file):
    tables = {}
    # 1. 读取输入文本，解析表结构
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    current_table = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 匹配表名
        section_match = re.match(r'\[([0-9A-Za-z_]{1,7})\]', line)
        if section_match:
            current_table = section_match.group(1).upper()
            tables[current_table] = []
            continue
        # 匹配条目
        entry_match = re.match(r'([0-9A-F]{8})=(.*)', line, re.IGNORECASE)
        if entry_match and current_table:
            hash_val = int(entry_match.group(1), 16)
            text = entry_match.group(2)
            tables[current_table].append((hash_val, text))
    
    # 2. MAIN 表必须第一个，其余保持原顺序（严格符合规范）
    table_names = []
    if 'MAIN' in tables:
        table_names.append('MAIN')
    table_names.extend([name for name in tables.keys() if name != 'MAIN'])
    num_tables = len(table_names)

    # 3. 文件头
    version = 4
    char_bits = 16
    buf = bytearray()
    buf += struct.pack('<HH', version, char_bits)

    # 4. TABL 块头
    tabl_magic = b'TABL'
    tabl_entry_size = 12
    tabl_size = num_tables * tabl_entry_size
    buf += tabl_magic + struct.pack('<I', tabl_size)

    # 5. 先计算每个表的偏移
    table_offsets = {}
    file_offset = 4 + 8 + tabl_size  # 文件头+TABL头+TABL表项

    for table_name in table_names:
        table_offsets[table_name] = file_offset  # 偏移必须指向表块开头

        entries = tables[table_name]
        # 如果不是 MAIN，先加 8字节表名
        if table_name != 'MAIN':
            file_offset += 8

        # TKEY
        tkey_data_size = len(entries) * 8
        file_offset += 8 + tkey_data_size  # 含头部+数据

        # TDAT
        str_total_len = sum(len(text.encode('utf-16le')) + 2 for _, text in entries)
        file_offset += 8 + str_total_len  # 含头部+数据

    # 6. 写 TABL 表项
    for table_name in table_names:
        name_padded = table_name.encode('ascii').ljust(8, b'\x00')
        buf += name_padded + struct.pack('<I', table_offsets[table_name])

    # 7. 写各表
    for table_name in table_names:
        entries = tables[table_name]

        # 非 MAIN 表先写表名
        if table_name != 'MAIN':
            buf += table_name.encode('ascii').ljust(8, b'\x00')

        # TKEY
        tkey_magic = b'TKEY'
        tkey_data_size = len(entries) * 8
        buf += tkey_magic + struct.pack('<I', tkey_data_size)

        str_offsets = []
        cur_off = 0
        for _, text in entries:
            str_offsets.append(cur_off)
            cur_off += len(text.encode('utf-16le')) + 2

        for (hash_val, _), str_off in zip(entries, str_offsets):
            buf += struct.pack('<II', str_off, hash_val)

        # TDAT
        tdat_magic = b'TDAT'
        tdat_data_size = sum(len(text.encode('utf-16le')) + 2 for _, text in entries)
        buf += tdat_magic + struct.pack('<I', tdat_data_size)

        for _, text in entries:
            buf += text.encode('utf-16le') + b'\x00\x00'

    # 8. 写入文件
    with open(output_file, 'wb') as f:
        f.write(buf)


# 调用示例
generate_gxt('gta4.txt', 'chinese.gxt')
