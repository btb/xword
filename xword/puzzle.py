NO_ERROR = 0
MISTAKE = 1
FIXED_MISTAKE = 2
CHEAT = 3

ACROSS = 0
DOWN = 1

def make_hash(data):
    try:
        from hashlib import md5
        m = md5()
    except:
        import md5
        m = md5.new()
    m.update(data)
    return m.hexdigest()

class BinaryFile:
    def __init__(self, filename=None):
        if type(filename) == type(''): f = file(filename, 'rb')
        else: f = filename
        
        self.data = list(f.read())
        f.close()
        self.index = 0

    def save(self, filename):
        f = file(filename, 'wb+')
        f.write(''.join(self.data))
        f.close()

    def seek(self, pos):
        self.index = pos

    def length(self):
        return len(self.data)

    def position(self):
        return self.index

    def write_char(self, c):
        self.data[self.index] = c
        self.index += 1

    def read_char(self):
        c = self.data[self.index]
        self.index += 1
        return c

    def read_byte(self):
        return ord(self.read_char())

    def read_chars(self, count):
        r = ''
        for i in range(count):
            r += self.read_char()
        return r

    def read_bytes(self, count):
        r = []
        for i in range(count):
            r.append(self.read_byte())
        return r

    def read_string(self):
        if self.index == len(self.data): return ''
        s = ''
        c = self.read_char()
        while ord(c) is not 0 and self.index < len(self.data):
            s += c
            c = self.read_char()

        return unicode(s, 'cp1252') # This is the Windows character set

    def hashcode(self):
        return make_hash(''.join(self.data))

class PersistentPuzzle:
    def __init__(self):
        self.responses = {}
        self.errors = {}
        self.clock = 0
        self.clock_running = False

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
        data = (width, height, int(self.clock), bin, int(self.clock_running))
        return '%d %d %d %s %d' % data

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
        pos += count
        bin2 = bin[pos:pos+count]

        try:
            pos += count + 1 # skip the space
            (self.clock_running, pos) = self.get_int(bin, pos)
        except ValueError:
            self.clock_running = False

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

        f.seek(0x32)
        self.locked = (f.read_byte() == 0x04)

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
            return s

        self.title = massage(f.read_string())
        self.author = massage(f.read_string())
        self.copyright = massage(f.read_string())

        self.clues = []

        def read_clue():
            clue = massage(f.read_string())
            self.clues.append(clue)
            return clue

        self.setup(read_clue)

        self.notebook = massage(f.read_string())

        while f.position() < f.length():
            code = f.read_chars(4)
            count = f.read_byte() + 256*f.read_byte()
            junk = f.read_bytes(2)
            data = f.read_bytes(count)
            zero = f.read_byte()
            self.process_section(code, data)

    def setup(self, read_clue):
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
        self.circles = {}
        number = 1
        for y in range(self.height):
            for x in range(self.width):
                # NYTimes: April 30, 2006
                is_fresh_x = (self.is_black(x-1, y)
                              and not self.is_black(x+1, y))
                is_fresh_y = (self.is_black(x, y-1)
                              and not self.is_black(x, y+1))

                if not self.is_black(x, y):
                    if is_fresh_x:
                        self.across_map[x, y] = number
                        self.across_clues[number] = read_clue()
                    else:
                        if self.across_map.has_key((x-1, y)):
                            self.across_map[x, y] = self.across_map[x-1, y]
                    
                    if is_fresh_y:
                        self.down_map[x, y] = number
                        self.down_clues[number] = read_clue()
                    else:
                        if self.down_map.has_key((x, y-1)):
                            self.down_map[x, y] = self.down_map[x, y-1]

                    if is_fresh_x or is_fresh_y:
                        self.is_across[number] = is_fresh_x
                        self.is_down[number] = is_fresh_y
                        self.number_map[number] = (x, y)
                        self.number_rev_map[x, y] = number
                        number += 1
                #else:
                #    self.across_map[x, y] = 0
                #    self.down_map[x, y] = 0
        self.max_number = number-1

    def process_section(self, code, data):
        if code == 'GEXT':
            index = 0
            for y in range(self.height):
                for x in range(self.width):
                    if data[index] == 0x80:
                        self.circles[x, y] = True
                    index += 1

    def hashcode(self):
        (width, height) = (self.width, self.height)

        data = [' ']*width*height
        for ((x, y), r) in self.responses.items():
            index = y * width + x
            if r == '.': data[index] = '1'
            else: data[index] = '0'

        s1 = ''.join(data)
        s2 = ';'.join(self.clues)

        return make_hash(s1 + s2)

    def save(self, fname):
        f = self.f
        f.seek(0x34 + self.width * self.height)
        for y in range(self.height):
            for x in range(self.width):
                c = self.responses[x, y]
                if c == '': c = '-'
                f.write_char(c)
        f.save(fname)

    def is_locked(self):
        return self.locked

    def is_black(self, x, y):
        return self.responses.get((x, y), '.') == '.'

    def is_circled(self, x, y):
        return self.circles.has_key((x, y))

    def is_empty(self):
        for ((x, y), r) in self.responses.items():
            if r != '.' and r != '': return False
        return True

    def is_word_filled(self, x, y, dir):
        if not self.is_mode_valid(x, y, dir): return False

        n = self.number(x, y, dir)
        (x, y) = self.number_map[n]
        hit = False
        while not hit:
            if self.responses[x, y] == '': return False
            ((x, y), hit) = self.next_cell(x, y, dir, 1, False)
        return True

    def clue(self, x, y, mode):
        assert self.is_mode_valid(x, y, mode)
        if mode is ACROSS: return self.across_clues[self.across_map[x, y]]
        if mode is DOWN: return self.down_clues[self.down_map[x, y]]

    def number(self, x, y, mode):
        assert self.is_mode_valid(x, y, mode)
        return self.mode_maps[mode][x, y]

    def cell_has_number(self, x, y):
        return self.number_rev_map.has_key((x, y))

    def number_of_cell(self, x, y):
        return self.number_rev_map[x, y]

    def cell_of_number(self, number):
        return self.number_map[number]

    def is_mode_valid(self, x, y, mode):
        return self.mode_maps[mode].has_key((x, y))

    def next_cell(self, x, y, mode, incr, skip_black):
        (x0, y0) = (x, y)
        while x >= 0 and x < self.width and y >= 0 and y < self.height:
            if mode is ACROSS: x += incr
            else: y += incr

            if not skip_black or not self.is_black(x, y): break
        
        if self.is_black(x, y): return ((x0, y0), True)
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
        if r == None:
            (x1, y1) = self.number_map[self.mode_maps[mode][x, y]]
            r = self.find_blank_cell_recursive(x1, y1, mode, incr)
            if r == None: return (x, y)
            else: return r
        else: return r

    def is_cell_correct(self, x, y):
        return self.responses[x, y] == self.answers[x, y]

    def is_puzzle_correct(self):
        for x in range(self.width):
            for y in range(self.height):
                if not self.is_black(x, y) and not self.is_cell_correct(x, y):
                    return False
        return True

    def is_puzzle_filled(self):
        for x in range(self.width):
            for y in range(self.height):
                if not self.is_black(x, y) and self.responses[x, y] == '':
                    return False
        return True

    def incr_number(self, x, y, mode, incr):
        assert self.is_mode_valid(x, y, mode)
        n = self.mode_maps[mode][x, y]
        while True:
            n += incr
            if not self.number_map.has_key(n): return 0
            if mode == ACROSS and self.is_across[n]: break
            if mode == DOWN and self.is_down[n]: break
        return n

    def initial_number(self, mode):
        n = 1
        while True:
            if mode == ACROSS and self.is_across[n]: break
            if mode == DOWN and self.is_down[n]: break
            n += 1
        return n

    def final_number(self, mode):
        n = self.max_number
        while True:
            if mode == ACROSS and self.is_across[n]: break
            if mode == DOWN and self.is_down[n]: break
            n -= 1
        return n

    def set_letter(self, x, y, c):
        self.responses[x, y] = c

    def get_letter(self, x, y):
        return self.responses[x, y]

    def get_answer(self, x, y):
        return self.answers[x, y]

    def get_error(self, x, y):
        return self.errors[x, y]

    def set_error(self, x, y, err):
        self.errors[x, y] = err

    def is_blank(self, x, y):
        return self.responses[x, y] == ''

    def get_cells(self):
        return self.responses.keys()
