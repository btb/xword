import puzzle

import gtk
import pango

MIN_BOX_SIZE = 24

class GridWidget:
    def __init__(self, puzzle, control):
        self.puzzle = puzzle
        self.control = control
        
        self.area = gtk.DrawingArea()
        self.dbuf = None

        self.pango = self.area.create_pango_layout('')
        self.area.connect('expose-event', self.expose_event)
        self.area.connect('configure-event', self.configure_event)
        self.area.set_flags(gtk.CAN_FOCUS)

        self.sw = gtk.ScrolledWindow()
        self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.sw.add_with_viewport(self.area)

        self.widget = self.sw
        self.set_puzzle(puzzle, control)

    def set_puzzle(self, puzzle, control):
        self.puzzle = puzzle
        self.control = control

        if puzzle:
            width = puzzle.width * MIN_BOX_SIZE
            height = puzzle.height * MIN_BOX_SIZE
            self.area.set_size_request(width+1, height+1)
        else:
            self.box_size = MIN_BOX_SIZE

        self.dbuf = None
        self.area.queue_draw_area(0, 0, 32768, 32768)

    def configure_event(self, area, event):
        width, height = event.width, event.height

        if self.puzzle:
            # Don't forget that 1px is needed for the R&B borders
            bw = int((width - 1) / self.puzzle.width)
            bh = int((height - 1) / self.puzzle.height)
            self.box_size = min(bw, bh)
            
            self.width = self.box_size * self.puzzle.width + 1
            self.height = self.box_size * self.puzzle.height + 1
            
            self.x = int((width - self.width) / 2)
            self.y = int((height - self.height) / 2)

            self.dbuf = None
        else:
            self.width = width
            self.height = height
            self.x = 0
            self.y = 0

    def expose_event(self, area, event):
        if self.puzzle:
            if not self.dbuf:
                self.draw_puzzle(0, self.puzzle.width-1,
                                 0, self.puzzle.height-1)

            srcx = event.area.x - self.x
            srcy = event.area.y - self.y
            area.window.draw_drawable(self.gc, self.dbuf,
                                      srcx, srcy,
                                      event.area.x, event.area.y,
                                      event.area.width, event.area.height)
        else:
            self.draw_empty()

    def draw_empty(self):
        pass

    def draw_puzzle(self, xmin, xmax, ymin, ymax):
        cm = self.area.get_colormap()
        self.white = cm.alloc_color('white')
        self.black = cm.alloc_color('black')
        self.realblack = cm.alloc_color('black')
        self.red = cm.alloc_color('red')
        self.hilite = cm.alloc_color('yellow')
        self.green = cm.alloc_color('lightgreen')
        self.gray = cm.alloc_color('lightblue')
        self.darkgray = cm.alloc_color('darkgray')

        num_size = int(self.box_size * 0.25)
        let_size = int(self.box_size * 0.45)
        msg_size = int(self.box_size * 0.85)
        self.num_font = pango.FontDescription('Sans %d' % num_size)
        self.let_font = pango.FontDescription('Sans %d' % let_size)
        self.msg_font = pango.FontDescription('Sans %d' % msg_size)

        if not self.dbuf:
            self.dbuf = gtk.gdk.Pixmap(self.area.window,
                                       self.width, self.height, -1)
            view = self.dbuf

            self.gc = view.new_gc(foreground = self.white,
                                  background = self.white)
            view.draw_rectangle(self.gc, True, 0, 0,
                                self.width, self.height)
        else:
            view = self.dbuf

        for y in range(ymin, ymax+1):
            for x in range(xmin, xmax+1):
                self.draw_box(x, y)

        return True

    def draw_triangle(self, x0, y0, color, filled):
        view = self.dbuf

        self.gc.set_foreground(color)
        length = int(self.box_size * 0.3)
        view.draw_polygon(self.gc, filled,
                          [(x0 + self.box_size - length, y0),
                           (x0 + self.box_size, y0),
                           (x0 + self.box_size, y0 + length)])
        self.gc.set_foreground(self.black)

    def draw_box_data(self, x0, y0, n, letter, error, circled):
        view = self.dbuf

        if circled:
            self.gc.set_foreground(self.darkgray)
            view.draw_arc(self.gc, False, x0+1, y0+1,
                          self.box_size-2, self.box_size-2, 0, 360*64)
            self.gc.set_foreground(self.black)

        self.pango.set_font_description(self.num_font)
        self.pango.set_text(n)
        view.draw_layout(self.gc, int(x0 + self.box_size*0.08), y0, self.pango)

        self.pango.set_font_description(self.let_font)
        self.pango.set_text(letter)
        (w, h) = self.pango.get_pixel_size()
        x1 = int(x0 + (self.box_size - w) / 2)
        y1 = int(y0 + self.box_size * 0.3)
        view.draw_layout(self.gc, x1, y1, self.pango)

        if error == puzzle.MISTAKE:
            view.draw_line(self.gc, x0, y0,
                           x0 + self.box_size, y0 + self.box_size)
            view.draw_line(self.gc, x0, y0 + self.box_size,
                           x0 + self.box_size, y0)
        elif error == puzzle.FIXED_MISTAKE:
            self.draw_triangle(x0, y0, self.black, True)
        elif error == puzzle.CHEAT:
            self.draw_triangle(x0, y0, self.red, True)
            self.draw_triangle(x0, y0, self.black, False)

    def draw_box(self, x, y):
        view = self.dbuf

        x0 = x*self.box_size
        y0 = y*self.box_size

        if self.puzzle.is_black(x, y): color = self.black
        elif self.control.is_highlight_ok(x, y): color = self.green
        elif self.control.is_highlight_bad(x, y): color = self.red
        elif self.control.is_highlight_none(x, y): color = self.white
        elif self.control.is_main_selection(x, y): color = self.hilite
        elif self.control.is_selected(x, y): color = self.gray
        else: color = self.white

        self.gc.set_foreground(color)
        view.draw_rectangle(self.gc, True, x0, y0,
                            self.box_size, self.box_size)

        self.gc.set_foreground(self.black)
        view.draw_rectangle(self.gc, False, x0, y0,
                            self.box_size, self.box_size)

        letter = self.puzzle.responses[x, y]
        error = self.puzzle.errors[x, y]
        circled = self.puzzle.is_circled(x, y)
        
        if self.puzzle.cell_has_number(x, y):
            n = str(self.puzzle.number_of_cell(x, y))
        else:
            n = ''

        self.draw_box_data(x0, y0, n, letter, error, circled)

    def translate_position(self, x, y):
        x -= self.x
        y -= self.y
        return (int(x / self.box_size), int(y / self.box_size))

    def update(self, x, y):
        self.draw_puzzle(x, x, y, y)
        x0 = self.x + x*self.box_size
        y0 = self.y + y*self.box_size
        self.area.queue_draw_area(x0, y0, self.box_size, self.box_size)

    def update_all(self):
        self.draw_puzzle(0, self.puzzle.width-1,
                         0, self.puzzle.height-1)
        self.area.queue_draw_area(0, 0, 32768, 32768)

    def pos_update(self, (x, y)):
        hadj = self.sw.get_hadjustment()
        vadj = self.sw.get_vadjustment()

        x0 = self.x + x*self.box_size
        y0 = self.y + y*self.box_size
        x1 = x0 + self.box_size
        y1 = y0 + self.box_size

        hbuf = int(hadj.page_size * 0.20)
        vbuf = int(vadj.page_size * 0.20)

        if x0 < hadj.value + hbuf:
            hadj.value = float(max(0, x0 - hbuf))
        if x1 > hadj.value + hadj.page_size - hbuf:
            hadj.value = float(min(hadj.upper - hadj.page_size,
                                   x1 - hadj.page_size + hbuf))

        if y0 < vadj.value + vbuf:
            vadj.value = float(max(0, y0 - vbuf))
        if y1 > vadj.value + vadj.page_size - vbuf:
            vadj.value = float(min(vadj.upper - vadj.page_size,
                                   y1 - vadj.page_size + vbuf))
