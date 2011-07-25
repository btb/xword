import gtk
import pango
import math

import puzzle

ACROSS = puzzle.ACROSS
DOWN = puzzle.DOWN

MAIN_FONT = 'Bitstream Charter 9'
BOLD_FONT = 'Bitstream Charter bold 9'
SPACER = 2
LABEL_SPACER = 15
MIN_HEIGHT = 50

def measure_text(layout, text):
    layout.set_text(text)
    return layout.get_size()[0] / pango.SCALE

def font_size(layout):
    return layout.get_size()[1] / pango.SCALE

def clue_area_width(context):
    clue_layout = context.create_pango_layout()
    clue_layout.set_font_description(pango.FontDescription(MAIN_FONT))
    spacer = '1000 Polite agreement'
    return measure_text(clue_layout, spacer)

class FontInfo:
    def __init__(self, context):
        self.context = context

        self.clue_layout = context.create_pango_layout()
        desc = pango.FontDescription(MAIN_FONT)
        self.clue_layout.set_font_description(desc)
        
        self.label_layout = context.create_pango_layout()
        desc = pango.FontDescription(BOLD_FONT)
        self.label_layout.set_font_description(desc)

        self.num_layout = context.create_pango_layout()
        desc = pango.FontDescription(BOLD_FONT)
        self.num_layout.set_font_description(desc)

        self.col_width = clue_area_width(context)
        self.num_width = measure_text(self.num_layout, '100 ')
        self.text_width = (self.col_width - self.num_width) * 1.0

        self.clue_layout.set_wrap(pango.WRAP_WORD_CHAR)
        self.clue_layout.set_width(int(self.text_width * pango.SCALE))

class LabelItem:
    def __init__(self, info, label, clue_item, extra_space):
        self.info = info
        self.label = label
        self.clue_item = clue_item
        self.extra_space = 0
        if extra_space: self.extra_space = LABEL_SPACER
        
        self.label_height = font_size(self.info.label_layout)

    def height(self):
        return (self.extra_space + self.label_height
                + SPACER + self.clue_item.height())

    def draw(self, cr, x, y):
        cr.move_to(x + self.info.num_width, y + self.extra_space)
        self.info.label_layout.set_text(self.label)
        cr.show_layout(self.info.label_layout)
        self.clue_item.draw(cr, x,
                            y + self.extra_space + self.label_height + SPACER)

class ClueItem:
    def __init__(self, info, n, text):
        self.info = info
        self.n = n
        self.text = text

        self.info.clue_layout.set_text(self.text)
        self.clue_height = font_size(self.info.clue_layout)

    def height(self):
        return self.clue_height

    def draw(self, cr, x, y):
        self.info.num_layout.set_text(str(self.n) + ' ')
        w = measure_text(self.info.num_layout, str(self.n) + ' ')

        cr.move_to(x + self.info.num_width - w, y)
        cr.show_layout(self.info.num_layout)

        cr.move_to(x + self.info.num_width, y)
        self.info.clue_layout.set_text(self.text)
        cr.show_layout(self.info.clue_layout)

class ClueLayout:
    def __init__(self, puzzle, context, col_heights):
        self.puzzle = puzzle

        self.info = FontInfo(context)

        self.col_heights = col_heights
        self.items = []

        self.measure_mode('ACROSS', ACROSS, False)
        self.measure_mode('DOWN', DOWN, True)
        self.layout_items()

    def measure_mode(self, label, mode, extra_space):
        first = True
        for n in range(1, self.puzzle.max_number+1):
            m = self.puzzle.mode_clues[mode]
            if m.has_key(n):
                clue = m[n]

                item = ClueItem(self.info, n, clue)
                if first: item = LabelItem(self.info, label, item, extra_space)
                first = False

                self.items.append(item)

    def try_layout(self, heights):
        col = 0
        v = 0
        first = True
        columns = [[]]
        for (i, item) in enumerate(self.items):
            if not first: v += SPACER
            first = False

            height = item.height()
            
            if v+height <= heights[col]:
                columns[col].append((v, item))
                v += height
            else:
                first = True
                v = 0
                col += 1
                if col >= len(heights):
                    return (False, columns, self.items[i:])
                columns.append([])
                columns[col].append((v, item))
                v += height

        return (True, columns, [])

    def layout_items(self):
        vspace = 0
        for item in self.items:
            vspace += item.height()

        total_vspace = 0
        for h in self.col_heights:
            total_vspace += h

        assert total_vspace >= vspace # FIXME

        ncols = len(self.col_heights)
        trunc = (total_vspace - vspace)/ncols * 1.2
        incr = (total_vspace - vspace)/ncols * 0.025
        while trunc > 0:
            heights = self.col_heights[:]
            for i in range(len(heights)):
                heights[i] -= trunc
                if heights[i] < MIN_HEIGHT: heights[i] = 0

            (ok, columns, rest) = self.try_layout(heights)
            if ok: break

            trunc -= incr
        else:
            assert False # FIXME

        self.columns = columns
        self.trunc = trunc

    def num_columns(self):
        return len(self.columns)

    def draw_column(self, col, cr, x0, y0):
        for (y, item) in self.columns[col]:
            item.draw(cr, x0, y0+y)

LEFT_TOP = 0
LEFT_BOT = 1
RIGHT_TOP = 2
RIGHT_BOT = 3

class PuzzlePrinter:
    settings = None
    page_setup = None
    place = None
    print_answers = False
    enlarged = False

    def __init__(self, puzzle):
        self.puzzle = puzzle

    def draw_banner(self, r):
        (left, top, right, bottom) = r

        h = bottom - top
        size = int(h * 0.7)
        layout = self.context.create_pango_layout()
        layout.set_text(self.puzzle.title)

        while size > 5:
            desc = pango.FontDescription('serif ' + str(size))
            layout.set_font_description(desc)
            if measure_text(layout, self.puzzle.title) < right-left: break
            size -= 1

        width = measure_text(layout, self.puzzle.title)
        x0 = left + (right - left - width)/2
        y0 = top + (h - font_size(layout)) / 2
        self.cr.move_to(x0, y0)
        layout.set_text(self.puzzle.title)
        self.cr.show_layout(layout)

    def draw_box(self, x, y, r):
        (left, top, right, bottom) = r
        cr = self.cr

        cr.rectangle(left, top, right-left, bottom-top)
        cr.stroke()

        if self.puzzle.is_black(x, y):
            cr.rectangle(left, top, right-left, bottom-top)
            cr.fill()

        if self.puzzle.is_circled(x, y):
            cr.arc((left+right)/2, (top+bottom)/2, self.box_size/2,
                   0, 2*math.pi)
            cr.stroke()

        if self.puzzle.cell_has_number(x, y):
            n = self.puzzle.number_of_cell(x, y)
            self.num_layout.set_text(str(n))
            cr.move_to(left + self.box_size*0.05, top + self.box_size*0.05)
            cr.show_layout(self.num_layout)

        if PuzzlePrinter.print_answers:
            w = measure_text(self.let_layout, self.puzzle.responses[x, y])
            self.let_layout.set_text(self.puzzle.responses[x, y])
            h = font_size(self.let_layout)
            x0 = left + (right - left - w)/2
            y0 = top + (bottom - top)*0.6 - h/2
            cr.move_to(x0, y0)
            cr.show_layout(self.let_layout)

    def min_puzzle_size(self, w, h):
        puzzle = self.puzzle

        self.banner_size = 18

        bw = w/float(puzzle.width)
        bh = (h - self.banner_size)/float(puzzle.height)
        box_size = int(min(bw, bh))
        self.box_size = box_size

        w = box_size * puzzle.width
        h = box_size * puzzle.height
        return (w, h + self.banner_size)

    def draw_puzzle(self, r):
        puzzle = self.puzzle
        box_size = self.box_size
        (left, top, right, bottom) = r

        w = box_size * puzzle.width
        h = box_size * puzzle.height

#        self.cr.rectangle(left, top, right-left, bottom-top)
#        self.cr.stroke()

        banner_box = (left, top, right, top + self.banner_size)
        self.draw_banner(banner_box)

        left += ((right - left) - w)/2
        top += self.banner_size

        self.num_layout = self.context.create_pango_layout()
        desc = pango.FontDescription('sans ' + str(box_size * 0.3))
        self.num_layout.set_font_description(desc)

        self.let_layout = self.context.create_pango_layout()
        desc = pango.FontDescription('sans ' + str(box_size * 0.6))
        self.let_layout.set_font_description(desc)

        for y in range(puzzle.height):
            for x in range(puzzle.width):
                r = (left + x*box_size,
                     top + y*box_size,
                     left + (x+1)*box_size,
                     top + (y+1)*box_size)
                self.draw_box(x, y, r)

    def draw_page(self, op, context, page_nr):
        self.context = context
        self.cr = context.get_cairo_context()
        self.cr.set_source_rgb(0, 0, 0)
        self.cr.set_line_width(0.5)

        w = context.get_width()
        h = context.get_height()
        (left, top, right, bottom) = (0, 0, w, h)

#        self.cr.rectangle(0, 0, w, h)
#        self.cr.stroke()

        col_width = clue_area_width(context)
        num_cols = int(w / col_width)
        inner_width = col_width * num_cols
        (left, right) = ((w - inner_width)/2, (w + inner_width)/2)

        if PuzzlePrinter.enlarged:
            size_w = w
            size_h = h
        elif h > w:
            size_w = (right - left) * 0.75
            size_h = (bottom - top)/2
        else:
            size_w = (right - left)/2
            size_h = (bottom - top) * 0.75

        (pw, ph) = self.min_puzzle_size(size_w, size_h)

        pw = int((pw + col_width - 1)/col_width) * col_width

        if PuzzlePrinter.enlarged:
            r = ((w - pw)/2, (h - ph)/2, (w + pw)/2, (h + ph)/2)
            inside_top = top
            inside_bot = bottom
        elif self.place == LEFT_TOP:
            r = (left, top, left+pw, top+ph)
            inside_top = top+ph
            inside_bot = bottom
        elif self.place == LEFT_BOT:
            r = (left, bottom-ph, left+pw, bottom)
            inside_top = top
            inside_bot = bottom-ph
        elif self.place == RIGHT_TOP:
            r = (right-pw, top, right, top+ph)
            inside_top = top+ph
            inside_bot = bottom
        elif self.place == RIGHT_BOT:
            r = (right-pw, bottom-ph, right, bottom)
            inside_top = top
            inside_bot = bottom-ph
        else:
            assert False

        def coltop(x0, x1):
            if x1 <= r[0] or x0 >= r[2]: return top
            else: return inside_top

        def colbot(x0, x1):
            if x1 <= r[0] or x0 >= r[2]: return bottom
            else: return inside_bot

        if PuzzlePrinter.enlarged:
            if page_nr == 0:
                self.draw_puzzle(r)
            else:
                heights = [bottom-top]*num_cols
                area = ClueLayout(self.puzzle, context, heights)
                for col in range(area.num_columns()):
                    area.draw_column(col, self.cr, left + col*col_width, top)
        else:
            heights = []
            for col in range(num_cols):
                x0 = left + col*col_width
                x1 = left + (col + 1)*col_width
                heights.append(colbot(x0, x1) - coltop(x0, x1))
            area = ClueLayout(self.puzzle, context, heights)
            for col in range(area.num_columns()):
                x0 = left + col*col_width
                x1 = left + (col + 1)*col_width
                area.draw_column(col, self.cr, left + col*col_width, coltop(x0, x1))
            self.draw_puzzle(r)

    def begin_print(self, op, context):
        if PuzzlePrinter.enlarged: op.set_n_pages(2)
        else: op.set_n_pages(1)

    def create_custom_widget(self, op):
        layouts = [
            ('Right bottom (best for righties)', RIGHT_BOT),
            ('Left bottom (best for lefties)', LEFT_BOT),
            ('Right top', RIGHT_TOP),
            ('Left top', LEFT_TOP)]
        self.buttons = {}

        op.set_custom_tab_label('Crossword Options')

        main_box = gtk.VBox()
        box1 = gtk.HBox()
        main_box.pack_start(box1, False, False)
        box1.show()
        main_box.set_border_width(15)

        frame = gtk.Frame('Puzzle placement')
        box1.pack_start(frame, False, False)
        frame.show()

        box = gtk.VButtonBox()
        box.set_layout(gtk.BUTTONBOX_START)
        frame.add(box)
        box.show()

        button = None
        for (label, sel) in layouts:
            button = gtk.RadioButton(button, label)
            box.add(button)
            button.show()
            self.buttons[sel] = button
            button.set_active(PuzzlePrinter.place == sel)

        button = gtk.CheckButton('Print your answers')
        button.show()
        self.print_answers_button = button
        button.set_active(PuzzlePrinter.print_answers)
        main_box.pack_start(button, False, False, padding=10)

        button = gtk.CheckButton('Print enlarged (use two pages)')
        button.show()
        self.enlarge_button = button
        button.set_active(PuzzlePrinter.enlarged)
        main_box.pack_start(button, False, False)

        return main_box

    def custom_widget_apply(self, op, main_box):
        for (sel, button) in self.buttons.items():
            if button.get_active(): place = sel

        self.place = place
        PuzzlePrinter.place = place

        PuzzlePrinter.print_answers = self.print_answers_button.get_active()
        PuzzlePrinter.enlarged = self.enlarge_button.get_active()

    def print_puzzle(self, win):
        op = gtk.PrintOperation()

        if PuzzlePrinter.settings != None:
            op.set_print_settings(PuzzlePrinter.settings)

        if PuzzlePrinter.page_setup != None:
            op.set_default_page_setup(PuzzlePrinter.page_setup)

        op.connect('begin-print', self.begin_print)
        op.connect('draw-page', self.draw_page)
        op.connect('create-custom-widget', self.create_custom_widget)
        op.connect('custom-widget-apply', self.custom_widget_apply)

        r = op.run(gtk.PRINT_OPERATION_ACTION_PRINT_DIALOG, win)
        if r == gtk.PRINT_OPERATION_RESULT_APPLY:
            PuzzlePrinter.settings = op.get_print_settings()

    def do_page_setup(self, win):
        if PuzzlePrinter.settings is None:
            PuzzlePrinter.settings = gtk.PrintSettings()

        r = gtk.print_run_page_setup_dialog(win,
                                            PuzzlePrinter.page_setup,
                                            PuzzlePrinter.settings)
        PuzzlePrinter.page_setup = r
