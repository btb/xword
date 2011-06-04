#!/usr/bin/python

__version__ = '2.0'

__license__ = '''
Copyright (c) 2005-2009,
  Bill McCloskey    <bill.mccloskey@gmail.com>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

3. The names of the contributors may not be used to endorse or promote
products derived from this software without specific prior written
permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
'''

# TODO:
# Verify puzzle checksums
# Fix printing (Windows bug, Linux bug, enlarge support)
# Test fresh install, install over old version
# Make sure keyboard shortcuts (including arrows & delete key) match AL
# Package everything into one script file
# Create Windows installer
# Possible problem: Open puzzle in locked mode, reopen in unlocked, close,
#   then when you run xword it opens back in locked

import puzzle
import controller
import grid
import printing

import pygtk
pygtk.require('2.0')
import gtk
import gtk.gdk
import gobject
import pango

try:
    x = gtk.PrintOperation
    has_print = True
except:
    has_print = False

import sys
import math
import time
import os, os.path
import pickle
import ConfigParser
import tempfile

CONFIG_DIR = os.path.expanduser(os.path.join('~', '.xword'))
def config_path(name):
    return CONFIG_DIR + '/' + name

HOME_PATH = os.path.join(os.getcwd(), os.path.dirname(sys.argv[0]))

stock_items = [
    ('xw-check-word', 'pixmaps/crossword-check.png'),
    ('xw-check-puzzle', 'pixmaps/crossword-check-all.png'),
    ('xw-solve-word', 'pixmaps/crossword-solve.png'),
    ('xw-clock', 'pixmaps/crossword-clock.png'),
    ]

layouts = [
    ('Only Puzzle', 'puzzle'),
    ('Right Side', ('H', 'puzzle', 550, ('V', 'across', 250, 'down'))),
    ('Left Side', ('H', ('V', 'across', 250, 'down'), 200, 'puzzle')),
    ('Left and Right', ('H', ('H', 'across', 175, 'puzzle'), 725, 'down')),
    ('Top', ('V', ('H', 'across', 450, 'down'), 200, 'puzzle')),
    ('Bottom', ('V', 'puzzle', 400, ('H', 'across', 450, 'down'))),
    ('Top and Bottom', ('V', 'across', 150, ('V', 'puzzle', 300, 'down')))
    ]

ACROSS = puzzle.ACROSS
DOWN = puzzle.DOWN

ui_description = '''
<ui>
  <menubar name="Menubar">
    <menu action="MenuFile">
      <menuitem action="Open"/>
      <menu action="MenuRecent">
        <menuitem action="Recent0"/>
        <menuitem action="Recent1"/>
        <menuitem action="Recent2"/>
        <menuitem action="Recent3"/>
        <menuitem action="Recent4"/>
      </menu>
      <menuitem action="Save"/>
      <menuitem action="AboutPuzzle"/>
      <separator/>
      <menuitem action="PageSetup"/>
      <menuitem action="Print"/>
      <separator/>
      <menuitem action="Close"/>
      <menuitem action="Quit"/>
    </menu>
    <menu action="MenuEdit">
      <menuitem action="ClearWord"/>
      <menuitem action="ClearPuzzle"/>
    </menu>
    <menu action="MenuHints">
      <menuitem action="CheckLetter"/>
      <menuitem action="CheckWord"/>
      <menuitem action="CheckPuzzle"/>
      <separator/>
      <menuitem action="SolveLetter"/>
      <menuitem action="SolveWord"/>
      <menuitem action="SolvePuzzle"/>
    </menu>
    <menu action="MenuPreferences">
      <menuitem action="SkipFilled"/>
      <menuitem action="StartTimer"/>
      <menu action="MenuLayout">
        <menuitem action="Lay0"/>
        <menuitem action="Lay1"/>
        <menuitem action="Lay2"/>
        <menuitem action="Lay3"/>
        <menuitem action="Lay4"/>
        <menuitem action="Lay5"/>
        <menuitem action="Lay6"/>
      </menu>
    </menu>
    <menu action="MenuHelp">
      <menuitem action="Shortcuts"/>
      <menuitem action="About"/>
    </menu>
  </menubar>
  <toolbar name="Toolbar">
    <toolitem action="AboutPuzzle"/>
    <toolitem action="Open"/>
    <toolitem action="Save"/>
    <toolitem action="Print"/>
    <separator/>
    <toolitem action="CheckWord"/>
    <toolitem action="CheckPuzzle"/>
    <toolitem action="SolveWord"/>
    <separator expand="true"/>
    <toolitem action="Clock"/>
  </toolbar>
</ui>
'''

def time_str(t):
    total = int(t)
    secs = total % 60
    mins = (total / 60) % 60
    hrs = (total / 3600)
    return "%d:%02d:%02d" % (hrs, mins, secs)

class ClueWidget:
    def __init__(self, control):
        self.control = control

        width = 0
        height = grid.MIN_BOX_SIZE

        self.area = gtk.DrawingArea()
        self.pango = self.area.create_pango_layout('')
        self.area.set_size_request(width, height)
        self.area.connect('expose-event', self.expose_event)
        self.area.connect('configure-event', self.configure_event)

        self.widget = self.area

    def set_controller(self, control):
        self.control = control
        self.update()

    def configure_event(self, area, event):
        self.width, self.height = event.width, event.height
        self.pango.set_width(self.width * pango.SCALE)
        
    def expose_event(self, area, event):
        view = self.area.window
        cm = view.get_colormap()
        self.black = cm.alloc_color('black')
        self.gc = view.new_gc(foreground = self.black)
        
        size = 14
        while True:
            font = pango.FontDescription('Sans %d' % size)
            self.pango.set_font_description(font)
            self.pango.set_text(self.control.get_selected_word())
            w, h = self.pango.get_pixel_size()

            if h <= self.height: break
            size -= 1

        x = (self.width - w) / 2
        y = (self.height - h) / 2
        view.draw_layout(self.gc, x, y, self.pango)

    def update(self):
        self.area.queue_draw_area(0, 0, self.width, self.height)

class StatusBar:
    def __init__(self):
        self.frame = gtk.Frame()
        self.hbox = gtk.HBox()
        self.left_label = gtk.Label('Label')
        self.right_label = gtk.Label('Label')
        self.hbox.pack_start(self.left_label, True, True)
        self.hbox.pack_end(self.right_label, False, False, 20)
        self.frame.add(self.hbox)
        self.frame.set_shadow_type(gtk.SHADOW_NONE)
        self.left_label.set_ellipsize(pango.ELLIPSIZE_END)
        self.left_label.set_alignment(0.0, 0.0)

    def set_status(self, msg):
        self.left_label.set_text(msg)

    def set_right_label(self, label):
        self.right_label.set_text(label)

class MainWindow:
    def __init__(self, fname=None):
        self.setup_config_dir()
        store = puzzle.PuzzleStore(config_path('crossword-recent'),
                                   config_path('crossword-recent-list'))
        self.puzzle_store = store

        recent = self.puzzle_store.recent_list()
        if fname == None and len(recent) >= 1:
            fname = self.puzzle_store.get_recent(recent[0][1])
            ask = False
        else:
            ask = True

        self.clock_time = 0.0
        self.clock_running = False

        self.puzzle = None
        self.control = controller.DummyController()

        self.skip_filled = False
        self.start_timer = False
        self.layout = 0
        self.window_size = (900, 600)
        self.maximized = False
        self.positions = layouts[self.layout][1]
        self.default_loc = None

        win = gtk.Window()
        self.win = win
        self.handler = win.connect('destroy', lambda w: self.exit())
        win.connect('size-allocate', self.resize_window)
        win.connect('window-state-event', self.state_event)

        self.read_config()

        win.resize(self.window_size[0], self.window_size[1])
        if self.maximized: win.maximize()
        
        vbox = gtk.VBox()
        win.add(vbox)
        vbox = vbox

        self.cur_layout = None

        self.create_ui()
        vbox.pack_start(self.menubar, False, False, 0)
        vbox.pack_start(self.toolbar, False, False, 0)

        self.create_widgets()
        self.setup_controller()

        self.show_title()

        self.vbox = gtk.VBox()
        vbox.pack_start(self.vbox, True, True, 0)

        self.cur_layout = self.generate_layout(self.positions)
        self.vbox.pack_start(self.cur_layout, True, True, 0)

        self.status_bar = StatusBar()
        vbox.pack_start(self.status_bar.frame, False, False, 0)

        self.timeout = gobject.timeout_add(100, self.idle_event)
        win.connect('key-press-event', self.key_event)

        self.enable_controls(False, False)

        win.show_all()

        if fname: self.do_open_file(fname, ask)

        self.control.signal()
        self.puzzle_widget.area.grab_focus()

    def show_title(self):
        title = 'Xword Puzzle'
        data = ''
        locked = False
        if self.puzzle:
            title = 'Xword Puzzle - %s' % self.puzzle.title
            data = self.puzzle.title + '  ' + self.puzzle.author
            locked = self.puzzle.is_locked()
        
        self.win.set_title(title)

    def enable_controls(self, enabled, locked):
        def enable(a, x):
            action = self.actiongroup.get_action(a)
            action.set_sensitive(x)

        enable('Save', enabled)
        enable('PageSetup', enabled)
        enable('Print', enabled)
        enable('AboutPuzzle', enabled)
        enable('ClearWord', enabled)
        enable('ClearPuzzle', enabled)
        enable('CheckLetter', enabled and not locked)
        enable('CheckWord', enabled and not locked)
        enable('CheckPuzzle', enabled and not locked)
        enable('SolveLetter', enabled and not locked)
        enable('SolveWord', enabled and not locked)
        enable('SolvePuzzle', enabled and not locked)
        enable('Clock', enabled)

    def setup_controller(self):
        self.control.connect('puzzle-finished', self.puzzle_finished)
        self.control.connect('puzzle-filled', self.puzzle_filled)
        self.control.connect('letter-update', self.letter_update)
        self.control.connect('box-update', self.puzzle_widget.update)
        self.control.connect('all-update', self.puzzle_widget.update_all)
        self.control.connect('pos-update', self.puzzle_widget.pos_update)
        self.control.connect('title-update', self.clue_widget.update)
        self.control.connect('across-update', self.across_update)
        self.control.connect('down-update', self.down_update)
        self.control.connect('check-result', self.check_result)

    def open_recent(self, index):
        (title, hashcode) = self.puzzle_store.recent_list()[index]
        fname = self.puzzle_store.get_recent(hashcode)
        self.do_open_file(fname)

    def do_open_file(self, fname, ask=True):
        if self.puzzle: self.write_puzzle()

        if self.clock_running:
            self.activate_clock(False)
        
        self.set_puzzle(puzzle.Puzzle(fname), ask)
        self.control = controller.PuzzleController(self.puzzle)
        self.setup_controller()
        self.clue_widget.set_controller(self.control)
        self.puzzle_widget.set_puzzle(self.puzzle, self.control)

        self.load_list(ACROSS)
        self.load_list(DOWN)
        self.enable_controls(True, self.puzzle.is_locked())

        self.puzzle_store.add_recent(self.puzzle)
        self.update_recent_menu()

        self.idle_event()
        self.letter_update(0, 0)

    def do_save_file(self, fname):
        self.default_loc = os.path.dirname(fname)
        self.puzzle.save(fname)

    def get_puzzle_file(self, puzzle):
        dir = config_path('crossword_puzzles')
        return os.path.join(dir, puzzle.hashcode())

    def load_puzzle(self, fname, f):
        pp = puzzle.PersistentPuzzle()
        try:
            pp.from_binary(f.read())
            
            self.puzzle.responses = pp.responses
            self.puzzle.errors = pp.errors
            self.clock_time = pp.clock
            if pp.clock_running:
                self.activate_clock(True)
        except:
            self.notify('The saved puzzle is corrupted. It will not be used.')
            os.remove(fname)

        f.close()

    def set_puzzle(self, puzzle, ask):
        self.clock_time = 0.0

        self.puzzle = puzzle
        if not self.puzzle: return

        self.show_title()

        fname = self.get_puzzle_file(puzzle)

        try: f = file(fname, 'r')
        except IOError: f = None

        fresh = True
        if f:
            if ask:
                opts = ['Start Over', 'Continue']
                msg = ('This puzzle has been opened before. Would you like to'
                       + ' continue where you left off?')
                if self.ask(msg, opts) == 1:
                    self.load_puzzle(fname, f)
                    fresh = False
            else:
                self.load_puzzle(fname, f)
                fresh = False

        msg = ('Opened puzzle "%s" by %s, %s'
               % (puzzle.title, puzzle.author, puzzle.copyright))
        self.status_bar.set_status(msg)

        if fresh and self.start_timer:
            self.activate_clock(True)

        if len(puzzle.notebook) > 0 and fresh:
            self.notify('This puzzle has a notebook attached:\n'
                        + puzzle.notebook)

    def write_puzzle(self):
        if not self.puzzle: return

        if self.puzzle.is_empty():
            fname = self.get_puzzle_file(self.puzzle)
            try: os.remove(fname)
            except: pass
        else:
            pp = puzzle.PersistentPuzzle()
            pp.responses = self.puzzle.responses
            pp.errors = self.puzzle.errors
            
            if self.clock_running:
                self.clock_time += (time.time() - self.clock_start)
            pp.clock = self.clock_time
            pp.clock_running = self.clock_running

            fname = self.get_puzzle_file(self.puzzle)
            f = file(fname, 'w+')
            f.write(pp.to_binary())
            f.close()

    def exit(self):
        self.write_puzzle()
        self.write_config()
        self.puzzle_store.write()
        gobject.source_remove(self.timeout)
        self.win.destroy()
        gtk.main_quit()

    def notify(self, msg, parent=None):
        if parent == None: parent = self.win
        dialog = gtk.MessageDialog(parent=parent,
                                   type=gtk.MESSAGE_INFO,
                                   buttons=gtk.BUTTONS_OK,
                                   message_format=msg)
        dialog.connect("response", lambda dlg, resp: dlg.destroy())
        dialog.show()

    def ask(self, msg, opts):
        dialog = gtk.MessageDialog(parent=self.win,
                                   flags=gtk.DIALOG_MODAL,
                                   type=gtk.MESSAGE_QUESTION,
                                   message_format=msg)

        for (i, opt) in enumerate(opts): dialog.add_button(opt, i)
        dialog.set_default_response(i)

        dialog.show()
        r = dialog.run()
        dialog.destroy()

        return r

    def show_about_puzzle(self):
        msg = 'Title: ' + self.puzzle.title + '\n'
        msg += 'Author: ' + self.puzzle.author + '\n'
        msg += 'Copyright: ' + self.puzzle.copyright
        if self.puzzle.notebook != '':
            msg += '\n\nNotebook:\n' + self.puzzle.notebook

        mmsg = '<b>Title:</b> ' + self.puzzle.title + '\n'
        mmsg += '<b>Author:</b> ' + self.puzzle.author + '\n'
        mmsg += '<b>Copyright:</b> ' + self.puzzle.copyright
        if self.puzzle.notebook != '':
            mmsg += '\n\n<b>Notebook:</b>\n' + self.puzzle.notebook
        
        dialog = gtk.MessageDialog(parent=self.win,
                                   type=gtk.MESSAGE_INFO,
                                   buttons=gtk.BUTTONS_OK,
                                   message_format=msg)
        try: dialog.set_markup(mmsg)
        except: pass
        dialog.connect("response", lambda dlg, resp: dlg.destroy())
        dialog.show()

    def show_keyboard_shortcuts(self):
        msg = ('arrow-key: Move around or change direction\n'
               'tab: Next word\n'
               'ctrl + tab: Previous word\n'
               'control + arrow-key: Move around without changing direction\n'
               'backspace: Back up and delete letter\n'
               'delete: Clear the current letter\n'
               'control + delete: Clear the current word\n'
               'space: Clear letter and move to next space\n'
               'control + backspace: Delete part of perpendicular word'
               )

        dialog = gtk.MessageDialog(parent=self.win,
                                   type=gtk.MESSAGE_INFO,
                                   buttons=gtk.BUTTONS_OK,
                                   message_format=msg)
        dialog.connect("response", lambda dlg, resp: dlg.destroy())
        dialog.show()

    def show_about(self):
        dialog = gtk.AboutDialog()
        try:
            dialog.set_transient_for(self.win)
            dialog.set_modal(True)
        except:
            pass
        dialog.set_name('Xword')
        dialog.set_version(__version__)
        dialog.set_license(__license__)
        dialog.set_authors(
            ['Bill McCloskey <bill.mccloskey@gmail.com>\n' +
             'Maemo Port: Bradley Bell <bradleyb@u.washington.edu>\n' +
             'and Terrence Fleury <terrencegf@gmail.com>'])
        dialog.set_website('http://x-word.org')
        dialog.set_website_label('x-word.org')

        dialog.connect('response', lambda *args: dialog.destroy())
        dialog.show()

    def create_widgets(self):
        self.widgets = {}

        vbox = gtk.VBox()
        
        clue = ClueWidget(self.control)
        vbox.pack_start(clue.widget, False, False, 0)
        self.clue_widget = clue

        puzzle = grid.GridWidget(self.puzzle, self.control)
        puzzle.area.connect('key-press-event', self.puzzle_key_event)
        vbox.pack_start(puzzle.widget, True, True, 0)
        self.puzzle_widget = puzzle

        self.widgets['puzzle'] = vbox

        puzzle.widget.connect('button-press-event', self.button_event, puzzle)

        self.tree_paths = {}
        self.trees = {}

        self.widgets['across'] = self.create_list(ACROSS)
        self.widgets['down'] = self.create_list(DOWN)
        self.load_list(ACROSS)
        self.load_list(DOWN)
            
    def generate_layout(self, layout):
        if type(layout) == str:
            return self.widgets[layout]
        else:
            if layout[0] == 'H': w = gtk.HPaned()
            elif layout[0] == 'V': w = gtk.VPaned()
            
            w.add1(self.generate_layout(layout[1]))
            w.add2(self.generate_layout(layout[3]))
            w.set_position(layout[2])
            w.show()
            
            return w

    def set_layout(self, index):
        if not self.cur_layout: return

        for w in self.widgets.values():
            p = w.get_parent()
            if p: p.remove(w)

        p = self.cur_layout.get_parent()
        if p: p.remove(self.cur_layout)
        
        self.cur_layout = None
        self.layout = index
        self.positions = layouts[index][1]
        self.cur_layout = self.generate_layout(self.positions)
        self.vbox.pack_start(self.cur_layout, True, True, 0)

        self.win.show_all()
        self.puzzle_widget.area.grab_focus()

    def get_layout(self, widget):
        kind = widget.get_name()
        if kind == 'GtkHPaned':
            children = widget.get_children()
            return ('H',
                    self.get_layout(children[0]),
                    widget.get_position(),
                    self.get_layout(children[1]))
        elif kind == 'GtkVPaned':
            children = widget.get_children()
            return ('V',
                    self.get_layout(children[0]),
                    widget.get_position(),
                    self.get_layout(children[1]))
        else:
            for (name, w) in self.widgets.items():
                if w is widget: return name

    def state_event(self, w, event):
        state = int(event.new_window_state)
        self.maximized = (state & gtk.gdk.WINDOW_STATE_MAXIMIZED) <> 0

    def resize_window(self, widget, allocation):
        if not self.maximized:
            self.window_size = self.win.get_size()

    def update_recent_menu(self):
        recent = self.puzzle_store.recent_list()
        for (i, (title, hashcode)) in enumerate(recent):
            action = self.actiongroup.get_action('Recent%d' % i)
            action.set_sensitive(True)
            action.set_property('label', title)

    def activate_clock(self, active):
        action = self.actiongroup.get_action('Clock')
        action.set_active(active)

    def is_clock_active(self):
        action = self.actiongroup.get_action('Clock')
        return action.get_active()

    def set_clock_time(self, t):
        action = self.actiongroup.get_action('Clock')
        action.set_property('label', time_str(t))
        action.set_property('is-important', True)

    def create_ui(self):
        icons = gtk.IconFactory()
        for (stock_id, filename) in stock_items:
            path = os.path.join(HOME_PATH, filename)
            pixbuf = gtk.gdk.pixbuf_new_from_file(path)
            iconset = gtk.IconSet(pixbuf)
            icons.add(stock_id, iconset)
        icons.add_default()

        ui = gtk.UIManager()
        
        accelgroup = ui.get_accel_group()
        self.win.add_accel_group(accelgroup)

        actiongroup = gtk.ActionGroup('XwordActions')
        self.actiongroup = actiongroup

        def mk(action, stock_id, label=None, tooltip=None):
            return (action, stock_id, label, None,
                    tooltip, self.action_callback)

        actiongroup.add_actions([
            mk('MenuFile', None, '_File'),
            mk('Open', gtk.STOCK_OPEN),
            mk('MenuRecent', None, 'Open recent'),
            mk('Save', gtk.STOCK_SAVE),
            mk('AboutPuzzle', gtk.STOCK_INFO, 'About puzzle'),
            mk('PageSetup', None, 'Page setup...'),
            mk('Print', gtk.STOCK_PRINT),
            mk('Close', gtk.STOCK_CLOSE),
            mk('Quit', gtk.STOCK_QUIT),

            mk('Recent0', None, 'No recent item'),
            mk('Recent1', None, 'No recent item'),
            mk('Recent2', None, 'No recent item'),
            mk('Recent3', None, 'No recent item'),
            mk('Recent4', None, 'No recent item'),

            mk('MenuEdit', None, 'Edit'),
            mk('ClearWord', None, 'Clear word'),
            mk('ClearPuzzle', None, 'Clear puzzle'),

            mk('MenuHints', None, 'Hints'),
            mk('CheckLetter', None, 'Check letter'),
            mk('CheckWord', 'xw-check-word', 'Check word', 'Check word'),
            mk('CheckPuzzle', 'xw-check-puzzle', 'Check puzzle',
               'Check puzzle'),
            mk('SolveLetter', None, 'Solve letter'),
            mk('SolveWord', 'xw-solve-word', 'Solve word', 'Solve word'),
            mk('SolvePuzzle', None, 'Solve puzzle'),

            mk('MenuPreferences', None, 'Preferences'),
            mk('MenuLayout', None, 'Layout'),
            mk('Lay0', None, ''),
            mk('Lay1', None, ''),
            mk('Lay2', None, ''),
            mk('Lay3', None, ''),
            mk('Lay4', None, ''),
            mk('Lay5', None, ''),
            mk('Lay6', None, ''),

            mk('MenuHelp', None, '_Help'),
            mk('Shortcuts', None, 'Keyboard shortcuts'),
            mk('About', None, 'About'),
            ])

        def mktog(action, stock_id, label, active):
            return (action, stock_id, label,
                    None, None, self.action_callback, active)

        actiongroup.add_toggle_actions([
            mktog('SkipFilled', None, 'Skip filled squares', self.skip_filled),
            mktog('StartTimer', None,
                  'Start timer automatically', self.start_timer),

            mktog('Clock', 'xw-clock', 'Clock', self.clock_running),
            ])            

        ui.insert_action_group(actiongroup, 0)
        ui.add_ui_from_string(ui_description)

        self.update_recent_menu()

        for (i, layout) in enumerate(layouts):
            action = self.actiongroup.get_action('Lay%d' % i)
            action.set_property('label', layout[0])

        self.menubar = ui.get_widget('/Menubar')
        self.toolbar = ui.get_widget('/Toolbar')

    def select_layout(self, index):
        if index <> self.layout: self.set_layout(index)

    def action_callback(self, action):
        name = action.get_property('name')
        if name == 'Quit':
            self.exit()
        elif name == 'Close':
            self.exit()
        elif name == 'SkipFilled':
            self.skip_filled = not self.skip_filled
        elif name == 'StartTimer':
            self.start_timer = not self.start_timer
        elif name == 'Open':
            self.open_file()
        elif name == 'Save':
            self.save_file()
        elif name == 'Print':
            self.print_puzzle()
        elif name == 'PageSetup':
            self.page_setup()
        elif name == 'About':
            self.show_about()
        elif name == 'AboutPuzzle':
            self.show_about_puzzle()
        elif name == 'Shortcuts':
            self.show_keyboard_shortcuts()
        elif name.startswith('Recent'):
            index = int(name[len('Recent'):])
            self.open_recent(index)
        elif name.startswith('Lay'):
            index = int(name[len('Lay'):])
            self.select_layout(index)
        elif name == 'CheckLetter':
            self.control.check_letter()
        elif name == 'CheckWord':
            self.control.check_word()
        elif name == 'CheckPuzzle':
            self.control.check_puzzle()
        elif name == 'SolveLetter':
            self.control.solve_letter()
        elif name == 'SolveWord':
            self.control.solve_word()
        elif name == 'SolvePuzzle':
            self.control.solve_puzzle()
        elif name == 'ClearWord':
            self.control.clear_word()
        elif name == 'ClearPuzzle':
            self.control.clear_puzzle()
        elif name == 'Clock':
            self.clock_running = not self.clock_running
            if self.clock_running:
                self.clock_start = time.time()
            else:
                self.clock_time += (time.time() - self.clock_start)

    def create_list(self, mode):
        if mode == ACROSS: label = 'Across'
        else: label = 'Down'

        tree = gtk.TreeView()
        renderer = gtk.CellRendererText()
        renderer.set_property('wrap-width', 200)
        renderer.set_property('wrap-mode', pango.WRAP_WORD_CHAR)
        column = gtk.TreeViewColumn(label, renderer,
                                    text=1, strikethrough=2)
        tree.append_column(column)
        tree.connect('row-activated', self.select_changed, mode)
        tree.set_property('can-focus', False)

        scroll = gtk.ScrolledWindow()
        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scroll.add(tree)

        self.trees[mode] = tree
        
        return scroll

    def load_list(self, mode):
        self.tree_paths[mode] = {}
        store = gtk.ListStore(int, str, bool)
        i = 0
        for (n, clue) in self.control.get_clues(mode):
            self.tree_paths[mode][n] = i
            store.append((n, '%d. %s' % (n, clue),
                          self.control.is_word_filled(mode, n)))
            i += 1

        self.trees[mode].set_model(store)

    def select_changed(self, tree, path, column, mode):
        store = tree.get_model()
        n = store.get_value(store.get_iter(path), 0)
        self.control.select_word(mode, n)
        
    def letter_update(self, x, y):
        (empty, filled) = self.control.count_cells()
        total = empty+filled
        if total == 0: pct = 0.0
        else: pct = float(filled)/total*100.0
        self.status_bar.set_right_label('%d of %d squares filled in (%.0f%%)'
                                        % (filled, total, pct))

        def update_mode(mode):
            if self.puzzle.is_mode_valid(x, y, mode):
                n = self.puzzle.number(x, y, mode)
                filled = self.control.is_word_filled(mode, n)
                store = self.trees[mode].get_model()
                it = store.get_iter(self.tree_paths[mode][n])
                store.set_value(it, 2, filled)

        update_mode(ACROSS)
        update_mode(DOWN)

    def across_update(self, an):
        if self.tree_paths.has_key(ACROSS):
            selection = self.trees[ACROSS].get_selection()
            selection.select_path(self.tree_paths[ACROSS][an])
            tree = self.trees[ACROSS]
            tree.scroll_to_cell(self.tree_paths[ACROSS][an])

    def down_update(self, dn):
        if self.tree_paths.has_key(DOWN):
            selection = self.trees[DOWN].get_selection()
            selection.select_path(self.tree_paths[DOWN][dn])
            tree = self.trees[DOWN]
            tree.scroll_to_cell(self.tree_paths[DOWN][dn])

    def idle_event(self):
        t = time.time()
        if self.clock_running:
            total = int(self.clock_time + (t - self.clock_start))
        else:
            total = int(self.clock_time)

        self.set_clock_time(total)

        self.control.idle_event()

        return True

    def button_event(self, widget, event, puzzle):
        if event.type is gtk.gdk.BUTTON_PRESS:
            x = event.x + puzzle.widget.get_hadjustment().get_value()
            y = event.y + puzzle.widget.get_vadjustment().get_value()
            (x, y) = puzzle.translate_position(x, y)
            mode = self.control.get_mode()
            if event.button is 3: mode = 1-mode
            self.control.change_position(x, y, mode)

    def key_event(self, item, event):
        name = gtk.gdk.keyval_name(event.keyval)
        
        c = self.control

        ctl = (event.state & gtk.gdk.CONTROL_MASK) != 0

        if name == 'Right': c.move(ACROSS, 1, change_dir=not ctl)
        elif name == 'Left': c.move(ACROSS, -1, change_dir=not ctl)
        elif name == 'Up': c.move(DOWN, -1, change_dir=not ctl)
        elif name == 'Down': c.move(DOWN, 1, change_dir=not ctl)
        elif name == 'BackSpace' and ctl: c.kill_perpendicular()
        elif name == 'BackSpace' and not ctl: c.back_space()
        elif name == 'Delete' and ctl: c.clear_word()
        elif name == 'Delete' and not ctl: c.clear_letter()
        elif name == 'space': c.forward_space()
        elif name == 'Return' or name == 'Tab': c.next_word(1)
        elif name == 'ISO_Left_Tab': c.next_word(-1)
        else: return False

        return True

    def puzzle_key_event(self, item, event):
        if (event.state & ~gtk.gdk.LOCK_MASK) != 0: return False

        name = gtk.gdk.keyval_name(event.keyval)
        if name is None:
            return False
        if len(name) is 1 and name.isalpha():
            if self.start_timer:
                self.activate_clock(True)
            self.control.input_char(self.skip_filled, name)
            return True
        else:
            return False

    def puzzle_finished(self):
        self.notify('You have solved the puzzle!')
        if self.clock_running:
            self.activate_clock(False)

    def puzzle_filled(self):
        self.notify('The puzzle is completely filled.')
        if self.clock_running:
            self.activate_clock(False)

    def check_result(self, correct):
        if correct: msg = 'No mistakes found'
        else: msg = 'Incorrect.'

        self.status_bar.set_status(msg)

    def open_file(self):
        dlg = gtk.FileChooserDialog("Open...",
                                    None,
                                    gtk.FILE_CHOOSER_ACTION_OPEN,
                                    (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                     gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dlg.set_default_response(gtk.RESPONSE_OK)
        if self.default_loc: dlg.set_current_folder(self.default_loc)

        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            fname = dlg.get_filename()
            dlg.destroy()
            self.do_open_file(fname)
        else:
            dlg.destroy()

    def save_file(self):
        dlg = gtk.FileChooserDialog("Save As...",
                                    None,
                                    gtk.FILE_CHOOSER_ACTION_SAVE,
                                    (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                     gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        dlg.set_default_response(gtk.RESPONSE_OK)
        if self.default_loc: dlg.set_current_folder(self.default_loc)

        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            self.do_save_file(save_dlg.get_filename())
        dlg.destroy()

    def page_setup(self):
        if has_print:
            pr = printing.PuzzlePrinter(self.puzzle)
            pr.do_page_setup(self.win)
        else:
            self.notify('Printing support is not available (need GTK 2.10+).')

    def print_puzzle(self):
        if has_print:
            pr = printing.PuzzlePrinter(self.puzzle)
            pr.print_puzzle(self.win)
        else:
            self.notify('Printing support is not available (need GTK 2.10+).')

    def read_config(self):
        c = ConfigParser.ConfigParser()
        c.read(config_path('crossword.cfg'))
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
            if c.has_option('options', 'default_loc'):
                self.default_loc = eval(c.get('options', 'default_loc'))

    def write_config(self):
        c = ConfigParser.ConfigParser()
        c.add_section('options')
        c.set('options', 'skip_filled', self.skip_filled)
        c.set('options', 'start_timer', self.start_timer)
        c.set('options', 'layout', self.layout)
        c.set('options', 'positions', repr(self.get_layout(self.cur_layout)))
        c.set('options', 'window_size', repr(self.window_size))
        c.set('options', 'maximized', repr(self.maximized))
        c.set('options', 'default_loc', repr(self.default_loc))
        c.write(file(config_path('crossword.cfg'), 'w'))

    def setup_config_dir(self):
        if not os.path.exists(CONFIG_DIR):
            def try_copy(fname):
                path1 = os.path.expanduser(os.path.join('~', '.' + fname))
                if os.path.exists(path1):
                    path2 = config_path(fname)
                    try: os.system('cp -r %s %s' % (path1, path2))
                    except: pass

            def try_make(fname):
                try: os.mkdir(config_path(fname))
                except OSError: pass

            os.mkdir(CONFIG_DIR)
            try_copy('crossword_puzzles')
            try_make('crossword_puzzles')
            try_copy('crossword.cfg')
            try_make('crossword-recent')

if __name__ == '__main__':
    if len(sys.argv) <> 2: fname = None
    else: fname = sys.argv[1]
        
    w = PuzzleWindow(fname)
    gtk.main()
