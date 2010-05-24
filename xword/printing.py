import gtk
import pango

import puzzle

ACROSS = 0
DOWN = 1

class PrintFont:
    def __init__(self, family, style, size):
        self.face = gnomeprint.font_face_find_from_family_and_style(family,
                                                                    style)
        self.font = gnomeprint.font_find_closest(self.face.get_name(), size)
        self.size = size

    def measure_text(self, s):
        w = 0.0
        for c in s:
            glyph = self.face.lookup_default(ord(c))
            w += self.face.get_glyph_width(glyph) * 0.001 *self.font.get_size()
        return w

class ClueArea:
    def __init__(self, puzzle, font_size, col_height_fun):
        self.puzzle = puzzle

        self.clue_font = PrintFont('Serif', 'Regular', font_size)
        self.label_font = PrintFont('Serif', 'Bold', font_size)

        spacer = 'This is the width of a column'
        self.col_width = self.clue_font.measure_text(spacer)
        self.num_width = self.clue_font.measure_text('100. ')
        self.text_width = (self.col_width - self.num_width) * 0.9

        self.col_height_fun = col_height_fun
        self.col_num = 0
        
        self.y = self.col_height_fun(0, self.col_width) - self.clue_font.size
        self.x = self.num_width

        self.items = []
        self.group_start = None
        self.setup()

    def add_item(self, x, y, font, text):
        self.items = self.items + [(x, y, font, text)]

    def nextcol(self):
        self.col_num += 1
        self.x += self.col_width

        x = self.x - self.num_width
        h = self.col_height_fun(x, x + self.col_width)
        self.y = h - self.clue_font.size

    def open_group(self):
        self.group_start = self.items
        if self.y < 0: self.nextcol()

    def close_group(self):
        if self.y < 0:
            self.items = self.group_start
            return False
        else:
            return True

    def draw(self, gpc, x0, y0):
        for (x, y, font, text) in self.items:
            gpc.setfont(font.font)
            gpc.moveto(x + x0, y + y0)
            gpc.show(text)

    def add_wrapped_text(self, width, font, text):
        words = text.split(' ')
        lines = []
        while len(words) > 0:
            w = 0.0
            line = []
            while len(words) > 0 and w < width:
                if len(line) > 0:
                    w += font.measure_text(' ')
                word = words.pop(0)
                line.append(word)
                w += font.measure_text(word)

            if w >= width and len(line) == 1:
                i = 0
                w = 0.0
                word = line[0]
                while True:
                    w += font.measure_text(word[i])
                    if w > width: break
                    i += 1
                line = [word[:i]]
                words = [word[i:]] + words
            elif w >= width:
                words = [line.pop()] + words
            lines.append(line)

        for line in lines:
            s = ' '.join(line)
            self.add_item(self.x, self.y, font, s)
            self.y -= font.size

    def add_space(self, pct):
        self.y -= self.clue_font.size * pct

    def add_label(self, label):
        start = self.x
        stop = self.x + self.text_width
        w = self.label_font.measure_text(label)
        x0 = start + (stop - start - w)/2

        self.add_item(x0, self.y, self.label_font, label)
        self.y -= self.label_font.size

    def add_column(self, name, mode):
        first = True
        for n in range(1, self.puzzle.max_number+1):
            m = self.puzzle.mode_clues[mode]
            if m.has_key(n):
                clue = m[n]
                num = '%d. ' % n
                nw = self.clue_font.measure_text(num)

                while True:
                    self.open_group()
                    if first:
                        self.add_label(name)
                        self.add_space(1.0)
                        
                    self.add_item(self.x - nw, self.y, self.clue_font, num)
                    self.add_wrapped_text(self.text_width,self.clue_font, clue)

                    if self.close_group(): break

                self.add_space(0.5)
                if first: first = False

    def setup(self):
        self.add_column('Across', ACROSS)
        self.add_space(1.0)
        self.add_column('Down', DOWN)

    def width(self):
        return (self.col_num + 1) * self.col_width

class PuzzlePrinter:
    def __init__(self, puzzle):
        self.puzzle = puzzle

    def draw_banner(self, r):
        (left, bottom, right, top) = r

        h = top - bottom
        size = int(h * 0.7)
        font = PrintFont('Serif', 'Regular', size)

        self.gpc.setfont(font.font)
        width = font.measure_text(self.puzzle.title)
        x0 = left + (right - left - width)/2
        y0 = top - size
        self.gpc.moveto(x0, y0)
        self.gpc.show(self.puzzle.title)

    def draw_box(self, x, y, r):
        (left, bottom, right, top) = r
        gpc = self.gpc

        gpc.rect_stroked(left, bottom, (right-left), (top-bottom))
        if self.puzzle.is_black(x, y):
            gpc.rect_filled(left, bottom, (right-left), (top-bottom))

        if self.puzzle.number_rev_map.has_key((x, y)):
            gpc.setfont(self.num_font.font)
            n = self.puzzle.number_rev_map[x, y]
            gpc.moveto(left + self.box_size*0.05, top - self.box_size*0.35)
            gpc.show(str(n))

        gpc.setfont(self.let_font.font)
        w = self.let_font.measure_text(self.puzzle.responses[x, y])
        x0 = left + (right - left - w)/2
        gpc.moveto(x0, bottom + self.box_size*0.2)
        gpc.show(self.puzzle.responses[x, y])

        if self.puzzle.errors[x, y] != NO_ERROR:
            gpc.moveto(right - self.box_size*0.3, top)
            gpc.lineto(right, top)
            gpc.lineto(right, top - self.box_size*0.3)
            gpc.fill()

    def min_puzzle_size(self, r):
        puzzle = self.puzzle
        (left, bottom, right, top) = r

        self.banner_size = 18

        bw = (right - left)/float(puzzle.width)
        bh = (top - bottom - self.banner_size)/float(puzzle.height)
        box_size = int(min(bw, bh))
        self.box_size = box_size

        w = box_size * puzzle.width
        h = box_size * puzzle.height
        return (w, h + self.banner_size)

    def draw_puzzle(self, r):
        puzzle = self.puzzle
        box_size = self.box_size
        (left, bottom, right, top) = r

        w = box_size * puzzle.width
        h = box_size * puzzle.height

        banner_box = (left, top - self.banner_size, right, top)
        self.draw_banner(banner_box)

        left += ((right - left) - w)/2
        top -= self.banner_size

        self.num_font = PrintFont('Sans', 'Regular', box_size * 0.3)
        self.let_font = PrintFont('Sans', 'Regular', box_size * 0.6)

        for y in range(puzzle.height):
            for x in range(puzzle.width):
                r = (left + x*box_size,
                     top - (y+1)*box_size,
                     left + (x+1)*box_size,
                     top - y*box_size)
                self.draw_box(x, y, r)

    def draw_clues(self, r, coltop):
        (left, bottom, right, top) = r

        maxw = right - left

        def coltoprel(x0, x1):
            return coltop(x0 + left, x1 + left) - bottom

        size = 12
        while True:
            area = ClueArea(self.puzzle, size, coltoprel)
            w = area.width()
            if w <= maxw: break
            size -= 1

        area.draw(self.gpc, left, bottom)
        return area.col_width

    def units(self, length):
        i = 0
        while i < len(length) and (length[i].isdigit() or length[i] == '.'):
            i += 1
        num = length[:i].strip()
        units = length[i:].strip()

        if units == '': return float(num)

        u = gnomeprint.unit_get_by_abbreviation(units)
        if u == None:
            print 'Bad unit:', length
            return 0.0
        return float(num) * u.unittobase
        
    def draw(self, config):
        w = self.units(config.get(gnomeprint.KEY_PAPER_WIDTH))
        h = self.units(config.get(gnomeprint.KEY_PAPER_HEIGHT))
        
        left = self.units(config.get(gnomeprint.KEY_PAGE_MARGIN_LEFT))
        top = self.units(config.get(gnomeprint.KEY_PAGE_MARGIN_TOP))
        right = self.units(config.get(gnomeprint.KEY_PAGE_MARGIN_RIGHT))
        bottom = self.units(config.get(gnomeprint.KEY_PAGE_MARGIN_BOTTOM))

        if config.get(gnomeprint.KEY_PAGE_ORIENTATION) == 'R90':
            (w, h) = (h, w)
            (left, bottom, right, top) = (bottom, left, top, right)

        right = w - right
        top = h - top
        banner_size = 14

        self.gpc.beginpage("1")

        #self.gpc.rect_stroked(left, bottom, right-left, top-bottom)

        if h > w:
            mid = (top + bottom) / 2
            r = (left, mid, right, top)
        else:
            mid = (left + right)/2
            r = (left, bottom, mid, top)

        (w, h) = self.min_puzzle_size(r)
        h += 0.05 * h

        def coltop(x0, x1):
            if ((x0 >= left and x0 <= left+w) or (x1 >= left and x1 <= left+w)
                or (x0 <= left and x1 >= left+w)):
                return top - h
            else:
                return top
            
        fullr = (left, bottom, right, top)
        col_width = self.draw_clues(fullr, coltop)

        w = int((w+col_width-1)/col_width) * col_width
        r = (r[0], r[1], left+w, r[3])
        self.draw_puzzle(r)

        self.gpc.showpage()

    def do_preview(self, config, dialog):
        job = gnomeprint.Job(config)
        self.gpc = job.get_context()
        job.close()
        self.draw(config)
        w = gnomeprint.ui.JobPreview(job, 'Print Preview')
        w.set_property('allow-grow', 1)
        w.set_property('allow-shrink', 1)
        w.set_transient_for(dialog)
        w.show_all()

    def do_print(self, dialog, res, job):
        config = job.get_config()

        if res == gnomeprint.ui.DIALOG_RESPONSE_CANCEL:
            dialog.destroy()
        elif res == gnomeprint.ui.DIALOG_RESPONSE_PREVIEW:
            self.do_preview(config, dialog)
        elif res == gnomeprint.ui.DIALOG_RESPONSE_PRINT:
            dialog.destroy()
            self.gpc = job.get_context()
            self.draw(config)
            job.close()
            job.print_()

    def print_puzzle(self, win):
        job = gnomeprint.Job(gnomeprint.config_default())
        dialog = gnomeprint.ui.Dialog(job, "Print...", 0)
        dialog.connect('response', self.do_print, job)
        dialog.set_transient_for(win)
        dialog.show()
