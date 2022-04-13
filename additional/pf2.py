'Python lib to read PF2 font file: http://grub.gibibit.com/New_font_format'

import io
from typing import Dict, Tuple

def uint32be(b: bytes):
    'Translate 4 bytes as unsigned big-endian 32-bit int'
    return (
        (b[0] << 32) +
        (b[1] << 16) +
        (b[2] << 8) +
        b[3]
    )

def int32be(b: bytes):
    'Translate 4 bytes as signed big-endian 32-bit int'
    u = uint32be(b)
    return u - ((u >> 31 & 0b1) << 32)

def uint16be(b: bytes):
    'Translate 2 bytes as big-endian unsigned 16-bit int'
    return (b[0] << 8) + b[1]

def int16be(b: bytes):
    'Translate 2 bytes as big-endian signed 16-bit int'
    u = uint16be(b)
    return u - ((u >> 15 & 0b1) << 16)

class Character():
    'A PF2 character'

    width: int
    height: int
    x_offset: int
    y_offset: int
    device_width: int
    bitmap_data: bytes


class PF2():
    'The PF2 class, for serializing a PF2 font file'

    is_pf2: bool
    'Sets to false if the read file is not PF2 font file'

    missing_character_code: int
    in_memory: bool

    font_name: str
    family: str
    weight: str
    slant: str
    point_size: int
    max_width: int
    max_height: int
    ascent: int
    descent: int
    character_index: Dict[int, Tuple[int, int]]
    data_offset: int
    data_io: io.IOBase

    def __init__(self, path='font.pf2', *, read_to_mem=False, missing_character: str='?'):
        self.missing_character_code = ord(missing_character)
        self.in_memory = read_to_mem
        file = open(path, 'rb')
        self.is_pf2 = (file.read(12) == b'FILE\x00\x00\x00\x04PFF2')
        if not self.is_pf2:
            return
        while True:
            name = file.read(4)
            data_length = int32be(file.read(4))
            if name == b'CHIX':
                self.character_index = {}
                for _ in range(data_length // (4 + 1 + 4)):
                    code_point = int32be(file.read(4))
                    compression = file.read(1)[0]
                    offset = int32be(file.read(4))
                    self.character_index[code_point] = (
                        compression, offset
                    )
                continue
            elif name == b'DATA':
                if read_to_mem:
                    self.data_io = io.BytesIO(file.read())
                    self.data_offset = -file.tell()
                    file.close()
                else:
                    self.data_io = file
                    self.data_offset = 0
                break
            data = file.read(data_length)
            if name == b'NAME':
                self.font_name = data
            elif name == b'FAMI':
                self.family = data
            elif name == b'WEIG':
                self.weight = data
            elif name == b'SLAN':
                self.slant = data
            elif name == b'PTSZ':
                self.point_size = uint16be(data)
            elif name == b'MAXW':
                self.max_width = uint16be(data)
            elif name == b'MAXH':
                self.max_height = uint16be(data)
            elif name == b'ASCE':
                self.ascent = uint16be(data)
            elif name == b'DESC':
                self.descent = uint16be(data)

    def get_char(self, char: str):
        'Get a character, returning a `Character` instance'
        char_point = ord(char)
        info = self.character_index.get(char_point)
        if info is None:
            info = self.character_index[self.missing_character_code]
        _compression, offset = info
        data = self.data_io
        data.seek(offset + self.data_offset)
        char = Character()
        char.width = uint16be(data.read(2))
        char.height = uint16be(data.read(2))
        char.x_offset = int16be(data.read(2))
        char.y_offset = int16be(data.read(2))
        char.device_width = int16be(data.read(2))
        char.bitmap_data = data.read(
            (char.width * char.height + 7) // 8
        )
        return char

    __getitem__ = get_char

    def close(self):
        'Close the data IO, if it\'s a real file'
        if not self.in_memory:
            self.data_io.close()