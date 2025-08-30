import struct
import os
import sys
import mmap
import numpy as np

# =======================
# 极致优化版 GXT 解析（兼容IV版本生成格式）
# =======================

class III:
    def hasTables(self):
        return False

    def parseTables(self, stream):
        return []

    def parseTKeyTDat(self, stream):
        # III极速优化：一次性读取TKEY和TDAT，批量numpy分割+批量解码
        size = findBlock(stream, 'TKEY')
        entry_count = size // 12
        if entry_count == 0:
            return []
        tkey_data = stream.read(size)
        # III 假设结构为 (offset:uint32, key:8 bytes)
        tkey_np = np.frombuffer(tkey_data, dtype=[('offset', '<u4'), ('key', 'S8')])
        offsets = tkey_np['offset']
        keys = [sys.intern(k.split(b'\x00')[0].decode(errors='ignore')) for k in tkey_np['key']]
        datSize = findBlock(stream, 'TDAT')
        TDat = stream.read(datSize)
        if datSize == 0:
            return list(zip(keys, [""] * len(keys)))
        arr = np.frombuffer(TDat, dtype=np.uint16)
        zero_idx = np.where(arr == 0)[0]
        starts = offsets // 2
        starts = np.clip(starts, 0, len(arr))
        ends = np.searchsorted(zero_idx, starts, side='left')
        ends = np.where(ends < len(zero_idx), zero_idx[ends], len(arr))
        values = []
        for i in range(entry_count):
            s = starts[i]
            e = ends[i]
            if s >= e:
                values.append(sys.intern(""))
                continue
            raw = arr[s:e].tobytes()
            try:
                v = raw.decode('utf-16le', errors='ignore')
            except Exception:
                v = ""
            v = v.rstrip('\x00')
            values.append(sys.intern(v))
        return list(zip(keys, values))

class VC:
    def hasTables(self):
        return True

    def parseTables(self, stream):
        return _parseTables(stream)

    def parseTKeyTDat(self, stream):
        # VC极速优化：一次性读取TKEY和TDAT，批量numpy分割+批量解码
        size = findBlock(stream, 'TKEY')
        entry_count = size // 12
        if entry_count == 0:
            return []
        tkey_data = stream.read(size)
        tkey_np = np.frombuffer(tkey_data, dtype=[('offset', '<u4'), ('key', 'S8')])
        offsets = tkey_np['offset']
        keys = [sys.intern(k.split(b'\x00')[0].decode(errors='ignore')) for k in tkey_np['key']]
        datSize = findBlock(stream, 'TDAT')
        TDat = stream.read(datSize)
        if datSize == 0:
            return list(zip(keys, [""] * len(keys)))
        arr = np.frombuffer(TDat, dtype=np.uint16)
        zero_idx = np.where(arr == 0)[0]
        starts = offsets // 2
        starts = np.clip(starts, 0, len(arr))
        ends = np.searchsorted(zero_idx, starts, side='left')
        ends = np.where(ends < len(zero_idx), zero_idx[ends], len(arr))
        values = []
        for i in range(entry_count):
            s = starts[i]; e = ends[i]
            if s >= e:
                values.append(sys.intern(""))
                continue
            raw = arr[s:e].tobytes()
            try:
                v = raw.decode('utf-16le', errors='ignore')
            except Exception:
                v = ""
            v = v.rstrip('\x00')
            values.append(sys.intern(v))
        return list(zip(keys, values))

class SA:
    def hasTables(self):
        return True

    def parseTables(self, stream):
        return _parseTables(stream)

    def parseTKeyTDat(self, stream):
        # SA极速优化：一次性读取TKEY和TDAT，批量分割，批量解码
        size = findBlock(stream, 'TKEY')
        entry_count = size // 8
        if entry_count == 0:
            return []
        tkey_bytes = stream.read(size)
        tkey_np = np.frombuffer(tkey_bytes, dtype=np.uint32).reshape(-1, 2)
        offsets = tkey_np[:, 0]
        crcs = tkey_np[:, 1]
        datSize = findBlock(stream, 'TDAT')
        TDat = stream.read(datSize)
        if datSize == 0:
            keys = [f"{crc:08X}" for crc in crcs]
            return list(zip(keys, [""] * len(keys)))
        arr = np.frombuffer(TDat, dtype=np.uint8)
        zero_idx = np.where(arr == 0)[0]
        starts = offsets
        starts = np.clip(starts, 0, len(arr))
        ends = np.searchsorted(zero_idx, starts, side='left')
        ends = np.where(ends < len(zero_idx), zero_idx[ends], len(arr))
        mv = memoryview(TDat)
        values = []
        for i in range(entry_count):
            s = starts[i]; e = ends[i]
            if s >= e:
                values.append(sys.intern(""))
                continue
            raw = mv[s:e]
            try:
                v = raw.tobytes().decode('utf-8', errors='strict')
            except Exception:
                try:
                    gbk_bytes = raw.tobytes()
                    ansi_bytes = gbk_bytes.decode('gbk', errors='strict').encode('cp1252', errors='replace')
                    v = ansi_bytes.decode('cp1252', errors='replace')
                except Exception:
                    v = raw.tobytes().decode('cp1252', errors='replace')
            v = v.rstrip('\x00')
            values.append(sys.intern(v))
        keys = [f"{crc:08X}" for crc in crcs]
        return list(zip(keys, values))

class IV:
    def hasTables(self):
        return True

    def parseTables(self, stream):
        return _parseTables(stream)

    def parseTKeyTDat(self, stream):
        """
        IV 版本解析：
        - 非 MAIN 表块会有 8 字节表名前缀，MAIN 表没有表名。
        - findBlock(stream, 'TKEY') 会定位到 TKEY 的 header 之后（流位置在数据区开始）。
        - 这里要在定位 TKEY 之前判断是否需要跳过表名。
        """
        # 先 peek 足够字节以判断当前位置是表名还是直接是 TKEY
        head = stream.peek(8)
        # 若已有至少4字节并且前4字节是 TKEY，则当前位置直接为 TKEY header（不应跳过）
        if len(head) >= 4 and head[:4] == b'TKEY':
            # 当前位置就是 TKEY header，findBlock 会定位并把流定位到 TKEY 数据区
            tkey_block_size = findBlock(stream, 'TKEY')
        else:
            # 当前位置不是 TKEY header，应该是表名（非 MAIN 表）
            # 为稳健性：如果 peek 小于 8 字节，仍尝试读取 8 字节表名（不会异常）
            # 跳过 8 字节表名后，再查找 TKEY header
            # 先尝试读取 8 字节（若不足则直接抛错）
            name_bytes = stream.read(8)
            if len(name_bytes) < 8:
                raise ValueError("遇到异常的表名或文件截断（表名不足8字节）。")
            tkey_block_size = findBlock(stream, 'TKEY')

        # IV TKEY 每条 8 字节（4 字节偏移 + 4 字节 CRC/hash）
        entry_count = int(tkey_block_size // 8)
        if entry_count == 0:
            return []

        # 读取 TKEY 数据并解析（小端 uint32）
        tkey_bytes = stream.read(tkey_block_size)
        tkey_np = np.frombuffer(tkey_bytes, dtype=np.uint32).reshape(-1, 2)
        offsets = tkey_np[:, 0].astype(np.int64)  # 字节偏移（相对于 TDAT 数据区起始 = 数据区第 0 字节）
        crcs = tkey_np[:, 1]

        # 读取 TDAT 块
        tdat_block_size = findBlock(stream, 'TDAT')
        TDat = stream.read(tdat_block_size)
        # 如果没有数据，则返回空字符串对应的条目
        if tdat_block_size == 0 or len(TDat) == 0:
            return [(f"{crc:08X}", "") for crc in crcs]

        # 将 TDAT 当作 UTF-16LE 的 uint16 数组处理（每 2 字节一个字符）
        arr = np.frombuffer(TDat, dtype=np.uint16)
        tdat_char_len = len(arr)  # 字符（uint16 单位）长度
        zero_idx = np.where(arr == 0)[0]  # 终止符位置（字符索引）

        # 计算每个字符串的字符级起始索引（offsets 是字节偏移）
        starts = (offsets // 2).astype(np.int64)
        starts = np.clip(starts, 0, tdat_char_len)

        # 查找每个 start 对应的第一个终止符索引
        if zero_idx.size == 0:
            # 没有任何终止符，全部取到末尾
            ends = np.full_like(starts, tdat_char_len)
        else:
            ends_idx = np.searchsorted(zero_idx, starts, side='left')
            ends = np.where(ends_idx < len(zero_idx), zero_idx[ends_idx], tdat_char_len)

        # 批量解码并处理越界
        values = []
        for i in range(entry_count):
            s = int(starts[i]); e = int(ends[i])
            if s >= e or s >= tdat_char_len:
                values.append(sys.intern(""))
                continue
            # 切片并转回字节再解码
            try:
                raw_bytes = arr[s:e].tobytes()
            except Exception:
                values.append(sys.intern(""))
                continue
            try:
                v = raw_bytes.decode('utf-16le', errors='ignore')
            except Exception:
                v = ""
            v = v.rstrip('\x00')
            values.append(sys.intern(v))

        keys = [f"{crc:08X}" for crc in crcs]
        return list(zip(keys, values))

def parseTKeyTDat_common(stream, entry_size, key_format, value_encoding):
    size = findBlock(stream, 'TKEY')
    entry_count = int(size / entry_size)
    key_struct = struct.Struct(key_format)
    tkey_data = stream.read(size)
    TKey = [key_struct.unpack_from(tkey_data, i * entry_size) for i in range(entry_count)]

    datSize = findBlock(stream, 'TDAT')
    TDat = stream.read(datSize)
    mv = memoryview(TDat)
    Entries = []
    append_entry = Entries.append
    tdat_len = len(TDat)

    if key_format == 'I8s':
        key_decode = lambda b: b.split(b'\x00')[0].decode(errors='ignore')
        offsets = [entry[0] for entry in TKey]
        offsets.append(tdat_len)  # 便于处理最后一条
        for i, entry in enumerate(TKey):
            offset = entry[0]
            key = key_decode(entry[1])
            if offset >= tdat_len:
                value = ""
            else:
                # 用下一个offset作为end，完全等价于原始分割逻辑
                next_offset = offsets[i + 1]
                end = next_offset
                raw = mv[offset:end]
                try:
                    value = raw.tobytes().decode(value_encoding, errors='ignore')
                    idx = value.find('\x00')
                    if idx != -1:
                        value = value[:idx]
                except UnicodeDecodeError:
                    value = raw.tobytes().decode('cp1252', errors='ignore')
                    idx = value.find('\x00')
                    if idx != -1:
                        value = value[:idx]
            append_entry((key, value))
    else:
        offsets = [entry[0] for entry in TKey]
        offsets.append(tdat_len)
        for i, entry in enumerate(TKey):
            offset = entry[0]
            key = f'{entry[1]:08X}'
            if offset >= tdat_len:
                value = ""
            else:
                next_offset = offsets[i + 1]
                end = next_offset
                raw = mv[offset:end]
                try:
                    value = raw.tobytes().decode(value_encoding, errors='ignore')
                    idx = value.find('\x00')
                    if idx != -1:
                        value = value[:idx]
                except UnicodeDecodeError:
                    value = raw.tobytes().decode('cp1252', errors='ignore')
                    idx = value.find('\x00')
                    if idx != -1:
                        value = value[:idx]
            append_entry((key, value))
    return Entries

def findBlock(stream, block):
    """
    在当前流位置向后查找 4 字节 magic（block），找到后将流定位到 magic 之后（即 header 后）
    并返回块数据大小（不含 magic+size 的 8 字节）。
    若未找到则抛出 ValueError。
    说明：stream 必须实现 .tell(), .seek(), .peek(size) 和底层 mmap 可通过 stream._mmap 访问长度。
    """
    block_bytes = block.encode('ascii')
    if len(block_bytes) != 4:
        raise ValueError("块标识必须为4字节 ASCII 字符串。")

    # 试图使用底层 mmap 直接扫描以获得准确且高效的定位
    # 要求 MemoryMappedFile 实现有 _mmap 属性（当前实现中存在）
    try:
        mmap_obj = stream._mmap
    except AttributeError:
        # 若没有 _mmap，则回退到基于 peek/seek 的逐字节查找
        start_pos = stream.tell()
        file_pos = start_pos
        # 获取文件长度（尝试使用 seek/tell）
        # 先定位到末尾获取长度
        stream.seek(0, os.SEEK_END)
        file_len = stream.tell()
        stream.seek(start_pos, os.SEEK_SET)

        while file_pos + 8 <= file_len:
            stream.seek(file_pos, os.SEEK_SET)
            head = stream.read(4)
            if head == block_bytes:
                # 读取 size（下一 4 字节 小端）
                size_bytes = stream.read(4)
                if len(size_bytes) < 4:
                    raise ValueError(f"在 {file_pos} 找到 {block} 标志但无法读取大小（文件截断）。")
                size = struct.unpack('<I', size_bytes)[0]
                # 定位到数据区（magic+size 已被读过），即文件指针在数据区开始
                return size
            file_pos += 1
        raise ValueError(f"GXT 文件中未找到 {block} 块（格式错误或文件截断）")

    # 使用 mmap 的快速查找
    start = stream.tell()
    file_len = len(mmap_obj)
    pos = start
    # 逐字节搜索，确保不会越界访问（需要至少 8 字节以读取 size）
    while pos + 8 <= file_len:
        if mmap_obj[pos:pos+4] == block_bytes:
            # 直接从 mmap 中读取 size（小端 uint32）
            size = struct.unpack_from('<I', mmap_obj, pos+4)[0]
            # 将流定位到 magic+size 后（即数据区起始）
            stream.seek(pos + 8, os.SEEK_SET)
            return size
        pos += 1

    # 未找到
    raise ValueError(f"GXT 文件中未找到 {block} 块（格式错误或文件截断）")

def getVersion(stream):
    bytes8 = stream.peek(8)[:8]

    # IV版本特征：头部2字（version,bits）占4字节
    if len(bytes8) >= 4:
        try:
            version, bits_per_char = struct.unpack('<HH', bytes8[:4])
            if version == 4 and bits_per_char == 16:
                return 'IV'
        except struct.error:
            pass

    # SA 版本判定（简化）
    if len(bytes8) >= 8 and bytes8[4:8] == b'TABL':
        # 进一步区分 SA-Mobile / SA 可由 bits 判断（若可用）
        try:
            version, bits = struct.unpack('<HH', bytes8[:4])
            return 'SA-Mobile' if bits == 16 else 'SA'
        except struct.error:
            return 'SA'

    # VC 版本：直接以 TABL 开头
    if bytes8[:4] == b'TABL':
        return 'VC'

    # III 版本：以 TKEY 开头
    if bytes8[:4] == b'TKEY':
        return 'III'

    return None

def getReader(version):
    if version == 'VC':
        return VC()
    if version in ('SA', 'SA-Mobile'):
        return SA()
    if version == 'III':
        return III()
    if version == 'IV':
        return IV()
    raise ValueError(f"不支持的GXT版本：{version}")

def _parseTables(stream):
    """解析 TABL 表，返回 (table_name, offset) 列表"""
    try:
        tabl_size = findBlock(stream, 'TABL')
    except ValueError:
        return []  # 未找到 TABL

    entry_count = tabl_size // 12  # 每项 12 字节（8 字节表名 + 4 字节偏移）
    Tables = []
    for _ in range(entry_count):
        raw = stream.read(12)
        if len(raw) < 12:
            break
        raw_name, offset = struct.unpack('<8sI', raw)
        # 表名为 ASCII，去除末尾 \x00
        table_name = raw_name.split(b'\x00')[0].decode('ascii', errors='replace').strip()
        if table_name:
            Tables.append((table_name, offset))
    return Tables

class MemoryMappedFile:
    """轻量化的 mmap 读取包装，提供 read/seek/peek/tell"""
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise FileNotFoundError(f"文件不存在：{filename}")
        self._file = open(filename, 'rb')
        self._mmap = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
        self._pos = 0

    def read(self, size):
        if size <= 0:
            return b''
        end_pos = min(self._pos + size, len(self._mmap))
        data = self._mmap[self._pos:end_pos]
        self._pos = end_pos
        return data

    def seek(self, offset, whence=os.SEEK_SET):
        if whence == os.SEEK_SET:
            self._pos = max(0, min(offset, len(self._mmap)))
        elif whence == os.SEEK_CUR:
            self._pos = max(0, min(self._pos + offset, len(self._mmap)))
        elif whence == os.SEEK_END:
            self._pos = max(0, min(len(self._mmap) + offset, len(self._mmap)))

    def peek(self, size):
        if size <= 0:
            return b''
        end_pos = min(self._pos + size, len(self._mmap))
        return self._mmap[self._pos:end_pos]

    def tell(self):
        return self._pos

    def close(self):
        self._mmap.close()
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
