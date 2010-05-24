import os

ACROSS = 0
DOWN = 1

NO_ERROR = 0
MISTAKE = 1
FIXED_MISTAKE = 2
CHEAT = 3

class BinaryFile:
    def __init__(self, filename=None):
        f = file(filename, 'rb')
        self.data = list(f.read())
        f.close()
        self.index = 0

    def save(self, filename):
        f = file(filename, 'wb+')
        f.write(''.join(self.data))
        f.close()

    def seek(self, pos):
        self.index = pos

    def write_char(self, c):
        self.data[self.index] = c
        self.index += 1

    def read_char(self):
        c = self.data[self.index]
        self.index += 1
        return c

    def read_byte(self):
        return ord(self.read_char())

    def read_string(self):
        if self.index == len(self.data): return ''
        s = ''
        c = self.read_char()
        while ord(c) is not 0 and self.index < len(self.data):
            s += c
            c = self.read_char()

        result = s
        ellipsis_char = 133
        result = result.replace(chr(ellipsis_char), '...')
        result = unicode(result, 'iso_8859-1')
        return result

    def hashcode(self):
        m = md5.new()
        m.update(''.join(self.data))
        return m.hexdigest()

class PersistentPuzzle:
    def __init__(self):
        self.responses = {}
        self.errors = {}
        self.clock = 0

    def get_size(self, m):
        width = 0
        height = 0
        for (x, y) in m.keys():
            if x > width: width = x
            if y > height: height = y
        width += 1
        height += 1

        return (width, height)

    def to_binary(self):
        (width, height) = self.get_size(self.responses)
        bin1 = [' ']*width*height
        bin2 = [' ']*width*height

        for ((x, y), r) in self.responses.items():
            index = y * width + x
            bin1[index] = self.responses[x, y]
            if bin1[index] == '': bin1[index] = chr(0)

        for ((x, y), r) in self.errors.items():
            index = y * width + x
            bin2[index] = chr(self.errors[x, y])

        bin = ''.join(bin1 + bin2)
        return '%d %d %d %s' % (width, height, int(self.clock), bin)

    def get_int(self, s, pos):
        pos0 = pos
        while pos < len(s) and s[pos].isdigit(): pos += 1
        return (int(s[pos0:pos]), pos)

    def from_binary(self, bin):
        pos = 0
        (width, pos) = self.get_int(bin, pos)
        pos += 1
        (height, pos) = self.get_int(bin, pos)
        pos += 1
        (self.clock, pos) = self.get_int(bin, pos)
        pos += 1

        count = width*height
        bin1 = bin[pos:pos+count]
        bin2 = bin[pos+count:]

        self.responses = {}
        self.errors = {}

        i = 0
        for y in range(height):
            for x in range(width):
                if bin1[i] == chr(0): self.responses[x, y] = ''
                else: self.responses[x, y] = bin1[i]
                self.errors[x, y] = ord(bin2[i])
                i += 1

class Puzzle:
    def __init__(self, filename):
        self.load_file(filename)

    def load_file(self, filename):
        f = BinaryFile(filename)
        self.f = f

        f.seek(0x2c)
        self.width = f.read_byte()
        self.height = f.read_byte()

        f.seek(0x34)
        self.answers = {}
        self.errors = {}
        for y in range(self.height):
            for x in range(self.width):
                self.answers[x, y] = f.read_char()
                self.errors[x, y] = NO_ERROR

        self.responses = {}
        for y in range(self.height):
            for x in range(self.width):
                c = f.read_char()
                if c == '-': c = ''
                self.responses[x, y] = c

        def massage(s):
            # skips unprintable characters
            snew = ''
            for c in s:
                if ord(c) >= ord(' ') and ord(c) <= ord('~'): snew += c
            return snew

        self.title = massage(f.read_string())
        self.author = massage(f.read_string())
        self.copyright = massage(f.read_string())

        self.clues = []
        clue = f.read_string()
        while clue:
            self.clues.append(clue)
            clue = f.read_string()

        self.all_clues = self.clues[:]

        self.setup()

    def setup(self):
        self.across_clues = {}
        self.down_clues = {}
        self.across_map = {}
        self.down_map = {}
        self.number_map = {}
        self.number_rev_map = {}
        self.mode_maps = [self.across_map, self.down_map]
        self.mode_clues = [self.across_clues, self.down_clues]
        self.is_across = {}
        self.is_down = {}
        number = 1
        for y in range(self.height):
            for x in range(self.width):
                is_fresh_x = self.is_black(x-1, y)
                is_fresh_y = self.is_black(x, y-1)

                if not self.is_black(x, y):
                    if is_fresh_x:
                        self.across_map[x, y] = number
                        if self.is_black(x+1, y):
                            self.across_clues[number] = ''
                        else:
                            self.across_clues[number] = self.clues.pop(0)
                    else: self.across_map[x, y] = self.across_map[x-1, y]
                    
                    if is_fresh_y:
                        self.down_map[x, y] = number
                        if self.is_black(x, y+1): # see April 30, 2006 puzzle
                            self.down_clues[number] = ''
                        else:
                            self.down_clues[number] = self.clues.pop(0)
                    else: self.down_map[x, y] = self.down_map[x, y-1]

                    if is_fresh_x or is_fresh_y:
                        self.is_across[number] = is_fresh_x
                        self.is_down[number] = is_fresh_y
                        self.number_map[number] = (x, y)
                        self.number_rev_map[x, y] = number
                        number += 1
                else:
                    self.across_map[x, y] = 0
                    self.down_map[x, y] = 0
        self.max_number = number-1

    def hashcode(self):
        (width, height) = (self.width, self.height)

        data = [' ']*width*height
        for ((x, y), r) in self.responses.items():
            index = y * width + x
            if r == '.': data[index] = '1'
            else: data[index] = '0'

        s1 = ''.join(data)
        s2 = ';'.join(self.all_clues)

        m = md5.new()
        m.update(s1 + s2)
        return m.hexdigest()

    def save(self, fname):
        f = self.f
        f.seek(0x34 + self.width * self.height)
        for y in range(self.height):
            for x in range(self.width):
                c = self.responses[x, y]
                if c == '': c = '-'
                f.write_char(c)
        f.save(fname)

    def is_black(self, x, y):
        return self.responses.get((x, y), '.') == '.'

    def clue(self, x, y, mode):
        if mode is ACROSS: return self.across_clues[self.across_map[x, y]]
        if mode is DOWN: return self.down_clues[self.down_map[x, y]]

    def number(self, x, y, mode):
        return self.mode_maps[mode][x, y]

    def next_cell(self, x, y, mode, incr, skip_black):
        (xo, yo) = (x, y)
        while True:
            if mode is ACROSS:
                if x+incr < 0 or x+incr >= self.width: return ((x, y), True)
                x += incr
            else:
                if y+incr < 0 or y+incr >= self.height: return ((x, y), True)
                y += incr

            if not skip_black or not self.is_black(x, y): break
            (xo, yo) = (x, y)

        if self.is_black(x, y): return ((xo, yo), True)
        else: return ((x, y), False)

    def find_blank_cell_recursive(self, x, y, mode, incr):
        if self.responses[x, y] == '' or self.errors[x, y] == MISTAKE:
            return (x, y)
        else:
            ((x, y), hit) = self.next_cell(x, y, mode, incr, False)
            if hit: return None
            else: return self.find_blank_cell_recursive(x, y, mode, incr)

    def find_blank_cell(self, x, y, mode, incr):
        r = self.find_blank_cell_recursive(x, y, mode, incr)
        if r == None: return (x, y)
        else: return r

    def is_cell_correct(self, x, y):
        return self.responses[x, y] == self.answers[x, y]

    def is_puzzle_correct(self):
        for x in range(self.width):
            for y in range(self.height):
                if not self.is_black(x, y) and not self.is_cell_correct(x, y):
                    return False
        return True

    def incr_number(self, x, y, mode, incr):
        n = self.mode_maps[mode][x, y]
        while True:
            n += incr
            if not self.number_map.has_key(n): return 0
            if mode == ACROSS and self.is_across[n]: break
            if mode == DOWN and self.is_down[n]: break
        return n

    def final_number(self, mode):
        n = self.max_number
        while True:
            if mode == ACROSS and self.is_across[n]: break
            if mode == DOWN and self.is_down[n]: break
            n -= 1
        return n
