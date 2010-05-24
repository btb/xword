import puzzle

import gtk
import pango

MIN_BOX_SIZE = 24

class PuzzleWidget:
    def __init__(self, puzzle, control):
        self.puzzle = puzzle
        self.control = control
        
        self.area = gtk.DrawingArea()
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
            self.area.set_size_request(width, height)
        else:
            self.box_size = MIN_BOX_SIZE

        self.area.queue_draw_area(0, 0, 32768, 32768)

    def configure_event(self, area, event):
        width, height = event.width, event.height

        if self.puzzle:
            bw = width / self.puzzle.width
            bh = height / self.puzzle.height
            self.box_size = min(bw, bh)
            
            self.width = self.box_size * self.puzzle.width
            self.height = self.box_size * self.puzzle.height
            
            self.x = (width - self.width) / 2
            self.y = (height - self.height) / 2
        else:
            self.width = width
            self.height = height
            self.x = 0
            self.y = 0

    def expose_event(self, area, event):
        if self.puzzle: self.draw_puzzle()
        else: self.draw_empty()

    def draw_empty(self):
        pass

    def draw_puzzle(self):
        view = self.area.window
        cm = view.get_colormap()
        self.white = cm.alloc_color('white')
        self.black = cm.alloc_color('black')
        self.red = cm.alloc_color('red')
        self.gray = cm.alloc_color('LightGray')

        num_size = int(self.box_size * 0.25)
        let_size = int(self.box_size * 0.45)
        self.num_font = pango.FontDescription('Sans %d' % num_size)
        self.let_font = pango.FontDescription('Sans %d' % let_size)

        self.gc = view.new_gc(foreground = self.white, background = self.white)
        view.draw_rectangle(self.gc, True, self.x, self.y,
                            self.width, self.height)

        self.gc.set_foreground(self.black)
        view.draw_rectangle(self.gc, False, self.x, self.y,
                            self.width, self.height)

        for y in range(self.puzzle.height):
            for x in range(self.puzzle.width):
                self.draw_box(x, y)
        
        return True

    def draw_triangle(self, x0, y0, color, filled):
        view = self.area.window

        self.gc.set_foreground(color)
        length = int(self.box_size * 0.3)
        view.draw_polygon(self.gc, filled,
                          [(x0 + self.box_size - length, y0),
                           (x0 + self.box_size, y0),
                           (x0 + self.box_size, y0 + length)])
        self.gc.set_foreground(self.black)

    def draw_box_data(self, x0, y0, n, letter, error):
        view = self.area.window

        self.pango.set_font_description(self.num_font)
        self.pango.set_text(n)
        view.draw_layout(self.gc, int(x0 + self.box_size*0.08), y0, self.pango)

        self.pango.set_font_description(self.let_font)
        self.pango.set_text(letter)
        (w, h) = self.pango.get_pixel_size()
        x1 = int(x0 + (self.box_size - w) / 2)
        y1 = int(y0 + self.box_size * 0.3)
        view.draw_layout(self.gc, x1, y1, self.pango)

        if error == MISTAKE:
            view.draw_line(self.gc, x0, y0,
                           x0 + self.box_size, y0 + self.box_size)
            view.draw_line(self.gc, x0, y0 + self.box_size,
                           x0 + self.box_size, y0)
        elif error == FIXED_MISTAKE:
            self.draw_triangle(x0, y0, self.black, True)
        elif error == CHEAT:
            self.draw_triangle(x0, y0, self.red, True)
            self.draw_triangle(x0, y0, self.black, False)

    def draw_box(self, x, y):
        view = self.area.window

        x0 = self.x + x*self.box_size
        y0 = self.y + y*self.box_size

        if self.control.is_main_selection(x, y): color = self.red
        elif self.control.is_selected(x, y): color = self.gray
        elif self.puzzle.is_black(x, y): color = self.black
        else: color = self.white

        self.gc.set_foreground(color)
        view.draw_rectangle(self.gc, True, x0, y0,
                            self.box_size, self.box_size)

        self.gc.set_foreground(self.black)
        view.draw_rectangle(self.gc, False, x0, y0,
                            self.box_size, self.box_size)

        letter = self.puzzle.responses[x, y]
        error = self.puzzle.errors[x, y]
        
        if self.puzzle.number_rev_map.has_key((x, y)):
            n = str(self.puzzle.number_rev_map[x, y])
        else:
            n = ''

        self.draw_box_data(x0, y0, n, letter, error)

    def translate_position(self, x, y):
        x -= self.x
        y -= self.y
        return (int(x / self.box_size), int(y / self.box_size))

    def update(self, x, y):
        x0 = self.x + x*self.box_size
        y0 = self.y + y*self.box_size
        self.area.queue_draw_area(x0, y0, self.box_size, self.box_size)
