import os.path
import ConfigParser
import csv
import StringIO

CONFIG_DIR = os.path.expanduser(os.path.join('~', '.xword'))
CONFIG_FILE = os.path.join(CONFIG_DIR, 'crossword.cfg')
CONFIG_RECENT_LIST = os.path.join(CONFIG_DIR, 'crossword-recent-list')
CONFIG_RECENT_DIR = os.path.join(CONFIG_DIR, 'crossword-recent')
CONFIG_PUZZLE_DIR = os.path.join(CONFIG_DIR, 'crossword_puzzles')

LAYOUTS = [
    ('Only Puzzle', 'puzzle'),
    ('Right Side', ('H', 'puzzle', 550, ('V', 'across', 250, 'down'))),
    ('Left Side', ('H', ('V', 'across', 250, 'down'), 200, 'puzzle')),
    ('Left and Right', ('H', ('H', 'across', 175, 'puzzle'), 725, 'down')),
    ('Top', ('V', ('H', 'across', 450, 'down'), 200, 'puzzle')),
    ('Bottom', ('V', 'puzzle', 400, ('H', 'across', 450, 'down'))),
    ('Top and Bottom', ('V', 'across', 150, ('V', 'puzzle', 300, 'down')))
    ]

PHASH = 0
PTITLE = 1

MAX_RECENT = 5

class XwordConfig:
    def __init__(self):
        self.set_defaults()
        self.setup_config_dir()

    def set_defaults(self):
        self.skip_filled = False
        self.start_timer = False
        self.layout = 0
        self.positions = LAYOUTS[self.layout][1]
        self.window_size = (900, 600)
        self.maximized = False
        self.organizer_window_size = (900, 600)
        self.organizer_maximized = False
        self.default_loc = None
        self.organizer_directories = []

    def read_config(self):
        c = ConfigParser.ConfigParser()
        c.read(CONFIG_FILE)
        if c.has_section('options'):
            if c.has_option('options', 'skip_filled'):
                self.skip_filled = c.getboolean('options', 'skip_filled')
            if c.has_option('options', 'start_timer'):
                self.start_timer = c.getboolean('options', 'start_timer')
            if c.has_option('options', 'layout'):
                self.layout = c.getint('options', 'layout')
            if c.has_option('options', 'positions'):
                self.positions = eval(c.get('options', 'positions'))
            if c.has_option('options', 'window_size'):
                self.window_size = eval(c.get('options', 'window_size'))
            if c.has_option('options', 'maximized'):
                self.maximized = eval(c.get('options', 'maximized'))
            if c.has_option('options', 'organizer_window_size'):
                self.organizer_window_size = eval(c.get('options', 'organizer_window_size'))
            if c.has_option('options', 'organizer_maximized'):
                self.organizer_maximized = eval(c.get('options', 'organizer_maximized'))
            if c.has_option('options', 'default_loc'):
                self.default_loc = eval(c.get('options', 'default_loc'))
            if c.has_option('options', 'organizer_directories'):
                self.organizer_directories = []
                dirs = c.get('options', 'organizer_directories')
                if len(dirs) > 0:
                    parser = csv.reader([dirs])
                    dirslist = []
                    for row in parser:
                        self.organizer_directories = row
                        break

    def write_config(self):
        c = ConfigParser.ConfigParser()
        c.add_section('options')
        c.set('options', 'skip_filled', self.skip_filled)
        c.set('options', 'start_timer', self.start_timer)
        c.set('options', 'layout', self.layout)
        c.set('options', 'positions', repr(self.positions))#self.get_layout(self.cur_layout)))
        c.set('options', 'window_size', repr(self.window_size))
        c.set('options', 'maximized', repr(self.maximized))
        c.set('options', 'organizer_window_size', repr(self.organizer_window_size))
        c.set('options', 'organizer_maximized', repr(self.organizer_maximized))
        c.set('options', 'default_loc', repr(self.default_loc))
        dirstring = StringIO.StringIO()
        if len(self.organizer_directories) > 0:
            writer = csv.writer(dirstring)
            writer.writerow(self.organizer_directories)
        c.set('options', 'organizer_directories', dirstring.getvalue().rstrip())
        c.write(file(CONFIG_FILE, 'w'))

    def set_skip_filled(self, skip_filled):
        self.read_config()
        self.skip_filled = skip_filled
        self.write_config()
        
    def get_skip_filled(self):
        self.read_config()
        return self.skip_filled
        
    def set_start_timer(self, start_timer):
        self.read_config()
        self.start_timer = start_timer
        self.write_config()
        
    def get_start_timer(self):
        self.read_config()
        return self.start_timer
        
    def set_layout(self, layout):
        self.read_config()
        self.layout = layout
        self.write_config()
        
    def get_layout(self):
        self.read_config()
        return self.layout
        
    def set_positions(self, positions):
        self.read_config()
        self.positions = positions
        self.write_config()
        
    def get_positions(self):
        self.read_config()
        return self.positions
        
    def set_window_size(self, window_size):
        self.read_config()
        self.window_size = window_size
        self.write_config()
        
    def get_window_size(self):
        self.read_config()
        return self.window_size
        
    def set_maximized(self, maximized):
        self.read_config()
        self.maximized = maximized
        self.write_config()
        
    def get_maximized(self):
        self.read_config()
        return self.maximized
        
    def set_organizer_window_size(self, organizer_window_size):
        self.read_config()
        self.organizer_window_size = organizer_window_size
        self.write_config()
        
    def get_organizer_window_size(self):
        self.read_config()
        return self.organizer_window_size
        
    def set_organizer_maximized(self, organizer_maximized):
        self.read_config()
        self.organizer_maximized = organizer_maximized
        self.write_config()
        
    def get_organizer_maximized(self):
        self.read_config()
        return self.organizer_maximized
        
    def set_default_loc(self, default_loc):
        self.read_config()
        self.default_loc = default_loc
        self.write_config()

    def get_default_loc(self):
        self.read_config()
        return self.default_loc

    def set_organizer_directories(self, organizer_directories):
        self.read_config()
        self.organizer_directories = organizer_directories
        self.write_config()
        
    def get_organizer_directories(self):
        self.read_config()
        return self.organizer_directories
        
    def setup_config_dir(self):
        if not os.path.exists(CONFIG_DIR):
            def try_copy(oldname, fname):
                path1 = os.path.expanduser(os.path.join('~', oldname))
                if os.path.exists(path1):
                    try: os.system('cp -r %s %s' % (path1, fname))
                    except: pass

            def try_make(fname):
                try: os.mkdir(fname)
                except OSError: pass

            os.mkdir(CONFIG_DIR)
            try_copy('.crossword_puzzles', CONFIG_PUZZLE_DIR)
            try_make(CONFIG_PUZZLE_DIR)
            try_copy('.crossword.cfg', CONFIG_FILE)
            try_make(CONFIG_RECENT_DIR)

    def get_puzzle_file(self, puzzle):
        return os.path.join(CONFIG_PUZZLE_DIR, puzzle.hashcode())

    def read_recent(self):
        try: data = eval(file(CONFIG_RECENT_LIST).read())
        except: data = []

        if type(data) == type([]):
            for x in data:
                if type(x) != type(()): data = []
                if len(x) != 2: data = []
        else:
            data = []

        self.recent = data

    def recent_list(self):
        self.read_recent()
        # Returns a (title, hashcode) list
        return [ (d[PTITLE], d[PHASH]) for d in self.recent ]

    def remove_recent(self, hash):
        self.read_recent()
        self.recent = [ d for d in self.recent if d[PHASH] != hash ]
        try: os.remove(os.path.join(CONFIG_RECENT_DIR, hash))
        except: pass
        self.write_recent()

    def add_recent(self, puzzle):
        hashcode = puzzle.hashcode()
        i = 0
        for d in self.recent:
            if d[PHASH] == hashcode:
                self.recent.pop(i)
                self.recent = [d] + self.recent
                self.write_recent()
                return
            i += 1

        if len(self.recent) >= MAX_RECENT:
            rmv = self.recent.pop()
            self.remove_recent(rmv[PHASH])

        d = (hashcode, puzzle.title)
        self.recent = [d] + self.recent
        puzzle.save(os.path.join(CONFIG_RECENT_DIR, hashcode))
        self.write_recent()

    def get_recent(self, hashcode):
        for d in self.recent:
            if d[PHASH] == hashcode:
                return os.path.join(CONFIG_RECENT_DIR, hashcode)

    def write_recent(self):
        f = file(CONFIG_RECENT_LIST, 'w')
        f.write(repr(self.recent))
        f.close()
