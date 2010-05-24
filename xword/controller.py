import puzzle

ACROSS = 0
DOWN = 1

class PuzzleController:
    def __init__(self, puzzle):
        self.puzzle = puzzle

        self.handlers = []
        self.selection = []

        self.mode = ACROSS
        (x, y) = (0, 0)
        if puzzle.is_black(x, y):
            ((x, y), _) = puzzle.next_cell(0, 0, ACROSS, 1, True)
        self.move_to(x, y)

    def connect(self, ev, handler):
        self.handlers.append((ev, handler))

    def do_update(self, signal_ev, *args):
        for (ev, h) in self.handlers:
            if ev == signal_ev: h(*args)

    def signal(self):
        self.move_to(self.x, self.y)

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

    def switch_mode(self):
        self.mode = 1-self.mode

        old_sel = self.selection
        self.selection = self.get_selection()

        for (x, y) in old_sel + self.selection:
            self.do_update('box-update', x, y)

        self.do_update('title-update')

    def move_to(self, x, y):
        if not self.puzzle.is_black(x, y):
            self.x = x
            self.y = y

            old_sel = self.selection
            self.selection = self.get_selection()

            for (xp, yp) in old_sel + self.selection:
                self.do_update('box-update', xp, yp)

            self.do_update('title-update')
            self.do_update('across-update', self.puzzle.number(x, y, ACROSS))
            self.do_update('down-update', self.puzzle.number(x, y, DOWN))

    def select_word(self, mode, n):
        if mode <> self.mode: self.switch_mode()
        (x, y) = self.puzzle.number_map[n]
        (x, y) = self.puzzle.find_blank_cell(x, y, mode, 1)
        self.move_to(x, y)

    def set_letter(self, letter):
        self.puzzle.responses[self.x, self.y] = letter
        if self.puzzle.errors[self.x, self.y] == MISTAKE:
            self.puzzle.errors[self.x, self.y] = FIXED_MISTAKE
            
        self.do_update('box-update', self.x, self.y)

        if self.puzzle.is_puzzle_correct():
            self.do_update('puzzle-finished')

    def erase_letter(self):
        self.set_letter('')

    def move(self, dir, amt, skip_black=True):
        if self.mode == dir:
            ((x, y), _) = self.puzzle.next_cell(self.x, self.y,
                                                self.mode, amt, skip_black)
            self.move_to(x, y)
        else:
            self.switch_mode()

    def back_space(self):
        if self.puzzle.responses[self.x, self.y] == '':
            self.move(self.mode, -1, False)
            self.erase_letter()
        else:
            self.erase_letter()

    def next_word(self, incr):
        n = self.puzzle.incr_number(self.x, self.y, self.mode, incr)
        if n == 0:
            self.switch_mode()
            if incr == 1: n = 1
            else: n = self.puzzle.final_number(self.mode)
        (x, y) = self.puzzle.number_map[n]
        (x, y) = self.puzzle.find_blank_cell(x, y, self.mode, 1)
        self.move_to(x, y)

    def input_char(self, skip_filled, c):
        c = c.upper()
        self.set_letter(c)
        ((x, y), hit) = self.puzzle.next_cell(self.x, self.y,
                                              self.mode, 1, False)
        if skip_filled:
            (x, y) = self.puzzle.find_blank_cell(x, y, self.mode, 1)

        self.move_to(x, y)

    def check_word(self):
        correct = True
        for (x, y) in self.selection:
            if not self.puzzle.is_cell_correct(x, y):
                if self.puzzle.responses[x, y] <> '':
                    self.puzzle.errors[x, y] = MISTAKE
                    correct = False
                    self.do_update('box-update', x, y)

        self.do_update('check-word-result', correct)

    def check_puzzle(self):
        correct = True
        for (x, y) in self.puzzle.responses.keys():
            if not self.puzzle.is_cell_correct(x, y):
                if self.puzzle.responses[x, y] <> '':
                    self.puzzle.errors[x, y] = MISTAKE
                    correct = False
                    self.do_update('box-update', x, y)

        self.do_update('check-puzzle-result', correct)

    def solve_word(self):
        for (x, y) in self.selection:
            if not self.puzzle.is_cell_correct(x, y):
                self.puzzle.errors[x, y] = CHEAT
                self.puzzle.responses[x, y] = self.puzzle.answers[x, y]
                self.do_update('box-update', x, y)
                    
        if self.puzzle.is_puzzle_correct():
            self.do_update('puzzle-finished')

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

class DummyController:
    def __init__(self):
        pass

    def connect(self, ev, handler):
        pass

    def signal(self):
        pass

    def switch_mode(self):
        pass

    def move_to(self, x, y):
        pass

    def select_word(self, mode, n):
        pass

    def set_letter(self, letter):
        pass

    def erase_letter(self):
        pass

    def move(self, dir, amt):
        pass

    def back_space(self):
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

    def is_selected(self, x, y):
        return False

    def is_main_selection(self, x, y):
        return False

    def get_selected_word(self):
        return 'Welcome. Please open a puzzle.'

    def get_clues(self, mode):
        return []
