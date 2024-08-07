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
        return parseTKeyTDat_common(stream, entry_size=12, key_format='I8s', value_encoding='utf-16')

class VC:
    def hasTables(self):
        return True

    def parseTables(self, stream):
        return _parseTables(stream)

    def parseTKeyTDat(self, stream):
        return parseTKeyTDat_common(stream, entry_size=12, key_format='I8s', value_encoding='utf-16')

class SA:
    def __init__(self):
        pass

    def hasTables(self):
        return True

    def parseTables(self, stream):
        return _parseTables(stream)

    def parseTKeyTDat(self, stream):
        return parseTKeyTDat_common(stream, entry_size=8, key_format='II', value_encoding='utf-8')

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
                if entry_bytes_start_offset + entry_bytes_cur_offset + 2 > len(TDat):
                    break
                unicode_char, = struct.unpack('H', TDat[entry_bytes_start_offset + entry_bytes_cur_offset:entry_bytes_start_offset + entry_bytes_cur_offset + 2])
                entry_bytes_cur_offset += 2
                if unicode_char != 0:
                    dat_str += chr(unicode_char)
                else:
                    break
            
            Entries.append((f'{crc:08X}', dat_str))

        return Entries

def parseTKeyTDat_common(stream, entry_size, key_format, value_encoding):
    size = findBlock(stream, 'TKEY')
    TKey = []
    for i in range(int(size / entry_size)):  # Entry size depends on the version
        TKey.append(struct.unpack(key_format, stream.read(entry_size)))

    datSize = findBlock(stream, 'TDAT')
    TDat = stream.read(datSize)

    Entries = []

    for entry in TKey:
        key = entry[1] if isinstance(entry[1], bytes) else f'{entry[1]:08X}'
        try:
            value = TDat[entry[0]:].decode(value_encoding, errors='ignore').split('\x00', 1)[0]
        except UnicodeDecodeError:
            value = TDat[entry[0]:].decode('cp1252', errors='ignore').split('\x00', 1)[0]
        Entries.append((key.split(b'\x00')[0].decode() if isinstance(key, bytes) else key, value))

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
        return 'IV'

    # SA
    word1, word2 = struct.unpack('HH', bytes[:4])
    if word1 == 4 and bytes[4:] == b'TABL':
        if word2 == 8:
            return 'SA'
        if word2 == 16:
            return 'SA-Mobile'

    if bytes[:4] == b'TABL':
        return 'VC'

    if bytes[:4] == b'TKEY':
        return 'III'

    return None

def getReader(version):
    if version == 'VC':
        return VC()
    if version == 'SA':
        return SA()
    if version == 'SA-Mobile':
        return SA()
    if version == 'III':
        return III()
    if version == 'IV':
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
