import struct
import os

class III:
    def __init__(self):
        pass

    def hasTables(self):
        return False  # III version doesn't have TABLEs

    def parseTables(self, stream):
        return []  # III version doesn't have TABLEs

    def parseTKeyTDat(self, stream):
        size = findBlock(stream, 'TKEY')

        TKey = []
        for i in range(int(size / 12)):  # TKEY entry size - 12
            TKey.append(struct.unpack('I8s', stream.read(12)))

        datSize = findBlock(stream, 'TDAT')
        TDat = stream.read(datSize)

        Entries = []

        for entry in TKey:
            key = entry[1]
            value = TDat[entry[0]:].decode('utf-16').split('\x00', 1)[0]
            Entries.append((key.split(b'\x00')[0].decode(), value))  # TODO: charmap

        return Entries

class VC:
    def hasTables(self):
        return True

    def parseTables(self, stream):
        return _parseTables(stream)

    def parseTKeyTDat(self, stream):
        size = findBlock(stream, 'TKEY')

        TKey = []
        for i in range(int(size / 12)):  # TKEY entry size - 12
            TKey.append(struct.unpack('I8s', stream.read(12)))

        datSize = findBlock(stream, 'TDAT')
        TDat = stream.read(datSize)

        Entries = []

        for entry in TKey:
            key = entry[1]
            value = TDat[entry[0]:].decode('utf-16').split('\x00', 1)[0]
            Entries.append((key.split(b'\x00')[0].decode(), value))  # TODO: charmap

        return Entries

class SA:
    def __init__(self):
        pass

    def hasTables(self):
        return True

    def parseTables(self, stream):
        return _parseTables(stream)

    def parseTKeyTDat(self, stream):
        size = findBlock(stream, 'TKEY')

        TKey = []
        for i in range(int(size / 8)):  # TKEY entry size - 8
            TKey.append(struct.unpack('II', stream.read(8)))

        datSize = findBlock(stream, 'TDAT')
        TDat = stream.read(datSize)

        Entries = []

        for entry in TKey:
            key = f'{entry[1]:08X}'
            value = TDat[entry[0]:].decode('utf-8', errors='ignore')  # Try decoding with UTF-8 first
            if not value:
                value = TDat[entry[0]:].decode('cp1252', errors='ignore')  # If UTF-8 fails, try cp1252
            value = value.split('\x00', 1)[0]

            Entries.append((key, value))  # TODO: charmap

        return Entries

class IV:
    def __init__(self):
        pass

    def hasTables(self):
        return True

    def parseTables(self, stream):
        return _parseTables(stream)

    def parseTKeyTDat(self, stream):
        size = findBlock(stream, 'TKEY')

        TKey = []
        for i in range(int(size / 8)):  # TKEY entry size - 8
            TKey.append(struct.unpack('II', stream.read(8)))

        datSize = findBlock(stream, 'TDAT')
        TDat = stream.read(datSize)

        Entries = []

        for entry in TKey:
            dat_offset, crc = entry
            entry_bytes_start_offset = dat_offset
            entry_bytes_cur_offset = 0
            dat_str = str()
            
            while True:
                unicode_char, = struct.unpack('H', TDat[entry_bytes_start_offset + entry_bytes_cur_offset:entry_bytes_start_offset + entry_bytes_cur_offset + 2])
                entry_bytes_cur_offset += 2
                if unicode_char != 0:
                    dat_str += chr(unicode_char)
                else:
                    break
            
            # TODO: 过滤/替换不支持的原版字符
            Entries.append((f'{crc:08X}', dat_str))

        return Entries

def findBlock(stream, block):
    while stream.peek(4)[:4] != block.encode():
        stream.seek(1, os.SEEK_CUR)

    _, size = struct.unpack('4sI', stream.read(8))

    return size

def getVersion(stream):
    bytes = stream.peek(8)[:8]

    # IV (Ensure this check is above SA checks to prevent incorrect matching)
    version, bits_per_char = struct.unpack('HH', bytes[:4])
    if version == 4 and bits_per_char == 16:
        return 'iv'

    # SA
    word1, word2 = struct.unpack('HH', bytes[:4])
    if word1 == 4 and bytes[4:] == b'TABL':
        if word2 == 8:
            return 'sa'
        if word2 == 16:
            return 'sa-mobile'

    if bytes[:4] == b'TABL':
        return 'vc'

    if bytes[:4] == b'TKEY':
        return 'iii'

    return None

def getReader(version):
    if version == 'vc':
        return VC()
    if version == 'sa':
        return SA()
    if version == 'sa-mobile':
        return SA()
    if version == 'iii':
        return III()
    if version == 'iv':
        return IV()
    return None

# Internal functions
def _parseTables(stream):
    size = findBlock(stream, 'TABL')
    Tables = []

    for i in range(int(size / 12)):  # TABL entry size - 12
        rawName, offset = struct.unpack('8sI', stream.read(12))
        Tables.append((rawName.split(b'\x00')[0].decode(), offset))

    return Tables
