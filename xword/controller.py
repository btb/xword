import puzzle

ACROSS = puzzle.ACROSS
DOWN = puzzle.DOWN

class PuzzleController:
    def __init__(self, puzzle):
        self.puzzle = puzzle

        self.handlers = []
        self.selection = []

        self.highlight_ok = {}
        self.highlight_bad = {}
        self.to_check = []
        self.checking = False
        self.check_rate = 0

        mode = ACROSS
        n = self.puzzle.initial_number(mode)
        (x, y) = self.puzzle.cell_of_number(n)
        self.change_position(x, y, mode)

    def connect(self, ev, handler):
        self.handlers.append((ev, handler))

    def do_update(self, signal_ev, *args):
        for (ev, h) in self.handlers:
            if ev == signal_ev: h(*args)

    def signal(self):
        self.change_position(self.x, self.y, self.mode)

    def get_selection(self):
        x, y, mode = self.x, self.y, self.mode

        sel = []
        if mode is ACROSS:
            index = x
            while not self.puzzle.is_black(index, y):
                sel.append((index, y))
                index -= 1
            index = x+1
            while not self.puzzle.is_black(index, y):
                sel.append((index, y))
                index += 1
        else:
            index = y
            while not self.puzzle.is_black(x, index):
                sel.append((x, index))
                index -= 1
            index = y+1
            while not self.puzzle.is_black(x, index):
                sel.append((x, index))
                index += 1
        return sel

    def get_mode(self):
        return self.mode

    def update_state(self):
        old_sel = self.selection
        self.selection = self.get_selection()

        for (xp, yp) in old_sel + self.selection:
            self.do_update('box-update', xp, yp)

        self.do_update('pos-update', (self.x, self.y))

        self.do_update('title-update')
        if self.puzzle.is_mode_valid(self.x, self.y, ACROSS):
            self.do_update('across-update',
                           self.puzzle.number(self.x, self.y, ACROSS))
        if self.puzzle.is_mode_valid(self.x, self.y, DOWN):
            self.do_update('down-update',
                           self.puzzle.number(self.x, self.y, DOWN))

    def change_position(self, x, y, mode):
        if not self.puzzle.is_black(x, y):
            self.x = x
            self.y = y

        self.mode = mode

        if not self.puzzle.is_mode_valid(self.x, self.y, self.mode):
            self.mode = 1-self.mode

        self.update_state()

    def select_word(self, mode, n):
        self.halt_check()

        (x, y) = self.puzzle.number_map[n]
        (x, y) = self.puzzle.find_blank_cell(x, y, mode, 1)

        assert self.puzzle.is_mode_valid(x, y, mode)

        self.change_position(x, y, mode)

    def set_letter(self, letter, x=None, y=None):
        self.halt_check()
        
        if x == None: x = self.x
        if y == None: y = self.y

        self.set_response(x, y, letter)
        if self.puzzle.get_error(x, y) == puzzle.MISTAKE:
            self.puzzle.set_error(x, y, puzzle.FIXED_MISTAKE)
            
        self.do_update('box-update', x, y)

        if not self.puzzle.is_locked() and self.puzzle.is_puzzle_correct():
            self.do_update('puzzle-finished')
        if self.puzzle.is_locked() and self.puzzle.is_puzzle_filled():
            self.do_update('puzzle-filled')

    # For a cell (x, y), when the direction is D, I find the word at (x, y)
    # in direction not(D). For each cell in that word, I check if the
    # perpendicular word is fully filled in. If it isn't, I delete the
    # value in that cell.
    def kill_perpendicular(self):
        self.halt_check()
        
        dir = 1-self.mode
        if self.puzzle.is_mode_valid(self.x, self.y, dir):
            n = self.puzzle.number(self.x, self.y, dir)
            (x, y) = self.puzzle.number_map[n]
            hit = False
            while not hit:
                if not self.puzzle.is_word_filled(x, y, 1-dir):
                    self.erase_letter(x, y)

                ((x, y), hit) = self.puzzle.next_cell(x, y, dir, 1, False)

    def erase_letter(self, x=None, y=None):
        self.halt_check()
        
        self.set_letter('', x, y)

    def move(self, dir, amt, skip_black=True, change_dir=True):
        self.halt_check()

        mode_valid = self.puzzle.is_mode_valid(self.x, self.y, dir)
        if self.mode <> dir and change_dir and mode_valid:
            self.change_position(self.x, self.y, dir)
        else:
            ((x, y), _) = self.puzzle.next_cell(self.x, self.y,
                                                dir, amt, skip_black)
            self.change_position(x, y, self.mode)

    def back_space(self):
        self.halt_check()
        
        self.erase_letter()
        self.move(self.mode, -1, False)

    def forward_space(self):
        self.halt_check()
        
        self.erase_letter()
        self.move(self.mode, 1, False)

    def next_word(self, incr):
        self.halt_check()
        
        n = self.puzzle.incr_number(self.x, self.y, self.mode, incr)
        if n == 0:
            mode = 1-self.mode
            if incr > 0: n = self.puzzle.initial_number(mode)
            else: n = self.puzzle.final_number(mode)
        else:
            mode = self.mode
        (x, y) = self.puzzle.cell_of_number(n)
        (x, y) = self.puzzle.find_blank_cell(x, y, mode, 1)
        self.change_position(x, y, mode)

    def input_char(self, skip_filled, c):
        self.halt_check()
        
        c = c.upper()
        self.set_letter(c)
        ((x, y), hit) = self.puzzle.next_cell(self.x, self.y,
                                              self.mode, 1, False)
        if skip_filled:
            (x, y) = self.puzzle.find_blank_cell(x, y, self.mode, 1)

        self.change_position(x, y, self.mode)

    def halt_check(self):
        if not self.checking: return
        while self.checking: self.idle_event()

    def check(self, cells):
        self.halt_check()
        
        self.to_check = cells[:]
        self.checking = True

        for (x, y) in self.to_check:
            self.do_update('box-update', x, y)

        def sortfun((x1, y1), (x2, y2)):
            n1 = x1+y1
            n2 = x2+y2
            return n2-n1
        
        self.to_check.sort(sortfun)
        self.check_rate = max(len(self.to_check)/5, 1)

    def check_letter(self):
        self.check([(self.x, self.y)])

    def check_word(self):
        self.check(self.selection)

    def check_puzzle(self):
        self.check(self.puzzle.get_cells())

    def check_complete(self):
        correct = True
        for (x, y) in self.highlight_bad.keys():
            self.puzzle.set_error(x, y, puzzle.MISTAKE)
            correct = False
            self.do_update('box-update', x, y)

        self.do_update('check-result', correct)

    def solve(self, cells):
        self.halt_check()
        
        was_correct = self.puzzle.is_puzzle_correct()
        was_filled = self.puzzle.is_puzzle_filled()

        for (x, y) in cells:
            if not self.puzzle.is_cell_correct(x, y):
                self.puzzle.set_error(x, y, puzzle.CHEAT)
                self.set_response(x, y, self.puzzle.get_answer(x, y))
                self.do_update('box-update', x, y)
                    
        if (not was_correct and not self.puzzle.is_locked()
            and self.puzzle.is_puzzle_correct()):
            self.do_update('puzzle-finished')
        if (not was_filled and self.puzzle.is_locked()
            and self.puzzle.is_puzzle_filled()):
            self.do_update('puzzle-filled')

    def solve_letter(self):
        self.solve([(self.x, self.y)])

    def solve_word(self):
        self.solve(self.selection)

    def solve_puzzle(self):
        self.solve(self.puzzle.get_cells())

    def clear(self, cells):
        self.halt_check()
        
        for (x, y) in cells:
            if not self.puzzle.is_black(x, y):
                self.set_response(x, y, '')
                self.do_update('box-update', x, y)

    def clear_letter(self):
        self.clear([(self.x, self.y)])

    def clear_word(self):
        self.clear(self.selection)

    def clear_puzzle(self):
        self.clear(self.puzzle.get_cells())

    def set_response(self, x, y, c):
        self.puzzle.set_letter(x, y, c)
        self.do_update('letter-update', x, y)

    def count_cells(self):
        empty = 0
        filled = 0
        for (x, y) in self.puzzle.get_cells():
            if self.puzzle.is_black(x, y): continue
            elif self.puzzle.is_blank(x, y): empty += 1
            else: filled += 1
        return (empty, filled)

    def is_word_filled(self, mode, n):
        (x, y) = self.puzzle.cell_of_number(n)
        return self.puzzle.is_word_filled(x, y, mode)

    def is_word_filled_at_position(self, x, y, mode):
        return self.puzzle.is_word_filled(x, y, mode)

    def is_highlight_ok(self, x, y):
        return self.highlight_ok.has_key((x, y))

    def is_highlight_bad(self, x, y):
        return self.highlight_bad.has_key((x, y))

    def is_highlight_none(self, x, y):
        return self.checking

    def is_selected(self, x, y):
        return ((x, y) in self.selection)

    def is_main_selection(self, x, y):
        return (x == self.x and y == self.y)

    def get_selected_word(self):
        return self.puzzle.clue(self.x, self.y, self.mode)

    def get_clues(self, mode):
        clues = []
        m = self.puzzle.mode_clues[mode]
        for n in range(1, self.puzzle.max_number+1):
            if m.has_key(n): clues.append((n, m[n]))
        return clues

    def idle_event(self):
        if self.checking:
            update = []

            if len(self.to_check) == 0:
                for c in self.highlight_ok.keys(): update.append(c)
                for c in self.highlight_bad.keys(): update.append(c)

                self.check_complete()
                self.highlight_ok = {}
                self.highlight_bad = {}
                self.checking = False
            else:
                n = self.check_rate
                while n > 0 and len(self.to_check) > 0:
                    n -= 1
                    (x, y) = self.to_check.pop()
                    update.append((x, y))
                    if self.puzzle.is_cell_correct(x, y) \
                           or self.puzzle.is_blank(x, y):
                        self.highlight_ok[(x, y)] = 1
                    else:
                        self.highlight_bad[(x, y)] = 1

            for (x, y) in update:
                self.do_update('box-update', x, y)

class DummyController:
    def __init__(self):
        pass

    def connect(self, ev, handler):
        pass

    def signal(self):
        pass

    def get_mode(self):
        return ACROSS

    def change_position(self, x, y, mode):
        pass

    def select_word(self, mode, n):
        pass

    def set_letter(self, letter):
        pass

    def kill_perpendicular(self):
        pass
    
    def erase_letter(self):
        pass

    def move(self, dir, amt, skip_black=True, change_dir=True):
        pass

    def back_space(self):
        pass

    def forward_space(self):
        pass
    
    def next_word(self, incr):
        pass

    def input_char(self, skip_filled, c):
        pass

    def check_word(self):
        pass

    def check_puzzle(self):
        pass

    def solve_word(self):
        pass

    def is_highlight_ok(self, x, y):
        return False

    def is_highlight_bad(self, x, y):
        return False

    def is_highlight_none(self, x, y):
        return False

    def is_selected(self, x, y):
        return False

    def is_main_selection(self, x, y):
        return False

    def get_selected_word(self):
        return 'Welcome. Please open a puzzle.'

    def get_clues(self, mode):
        return []

    def count_cells(self):
        return (0, 0)

    def idle_event(self):
        pass
