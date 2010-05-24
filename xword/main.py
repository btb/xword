#!/usr/bin/python
 
# Copyright (c) 2005-2006,
#   Bill McCloskey    <bill.mccloskey@gmail.com>
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.

# 3. The names of the contributors may not be used to endorse or promote
# products derived from this software without specific prior written
# permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import puzzle
import controller
import grid
import printing

import pygtk
pygtk.require('2.0')
import gtk
import gtk.gdk
import gobject

try:
    import gnomeprint
    import gnomeprint.ui
    has_print = True
except:
    has_print = False

import pango
import sys
import time
import os, os.path
import md5
import pickle
import ConfigParser

HOME_PATH = os.path.dirname(sys.argv[0])
CHECK_ICON = HOME_PATH + '/crossword-check.png'
CHECK_ALL_ICON = HOME_PATH + '/crossword-check-all.png'
SOLVE_ICON = HOME_PATH + '/crossword-solve.png'
TIMER_ICON = HOME_PATH + '/crossword-clock.png'

MIN_BOX_SIZE = 24

ACROSS = 0
DOWN = 1

NO_ERROR = 0
MISTAKE = 1
FIXED_MISTAKE = 2
CHEAT = 3

MENU_OPEN = 1
MENU_SAVE = 2
MENU_PRINT = 3
MENU_CLOSE = 4
MENU_QUIT = 5

MENU_SKIP = 10

layouts = [
    ('Only Puzzle', 'puzzle'),
    ('Right Side', ('H', 'puzzle', 550, ('V', 'across', 250, 'down'))),
    ('Left Side', ('H', ('V', 'across', 250, 'down'), 200, 'puzzle')),
    ('Left and Right', ('H', ('H', 'across', 175, 'puzzle'), 725, 'down')),
    ('Top', ('V', ('H', 'across', 450, 'down'), 200, 'puzzle')),
    ('Bottom', ('V', 'puzzle', 400, ('H', 'across', 450, 'down'))),
    ('Top and Bottom', ('V', 'across', 150, ('V', 'puzzle', 300, 'down')))
    ]

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
        height = MIN_BOX_SIZE

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

class PuzzleWindow:
    def __init__(self, puzzle):
        self.clock_time = 0.0
        self.clock_running = False

        self.win = None
        self.set_puzzle(puzzle)

        if self.puzzle: self.control = PuzzleController(self.puzzle)
        else: self.control = DummyController()

        self.skip_filled = False
        self.layout = 0
        self.window_size = (900, 600)
        self.maximized = False
        self.positions = layouts[self.layout][1]
        self.default_loc = None

        title = 'Crossword Puzzle'
        if self.puzzle: title = 'Crossword Puzzle - %s' % self.puzzle.title
        
        win = gtk.Window()
        self.handler = win.connect('destroy', lambda w: self.exit())
        win.set_title(title)
        win.connect('size-allocate', self.resize_window)
        win.connect('window-state-event', self.state_event)
        self.win = win

        self.read_config()

        win.resize(self.window_size[0], self.window_size[1])
        if self.maximized: win.maximize()
        
        vbox = gtk.VBox()
        win.add(vbox)
        vbox = vbox

        self.cur_layout = None

        self.menubar = self.create_menubar()
        self.toolbar = self.create_toolbar()
        vbox.pack_start(self.menubar, False, False, 0)
        vbox.pack_start(self.toolbar, False, False, 0)

        self.create_widgets()
        self.setup_controller()

        self.vbox = gtk.VBox()
        vbox.pack_start(self.vbox, True, True, 0)

        self.cur_layout = self.generate_layout(self.positions)
        self.vbox.pack_start(self.cur_layout, True, True, 0)

        self.status_bar = gtk.Statusbar()
        vbox.pack_start(self.status_bar, False, False, 0)

        gobject.timeout_add(500, self.idle_event)
        win.connect('key-press-event', self.key_event)

        if not self.puzzle: self.enable_controls(False)

        win.show_all()

        self.control.signal()
        self.puzzle_widget.area.grab_focus()

    def enable_controls(self, enabled):
        def enable(w): w.set_property('sensitive', enabled)
        
        enable(self.menu_items['save'])
        enable(self.menu_items['print'])
        enable(self.toolbar_items['Check Word'])
        enable(self.toolbar_items['Check Puzzle'])
        enable(self.toolbar_items['Solve Word'])
        enable(self.clock_button)

    def setup_controller(self):
        self.control.connect('puzzle-finished', self.puzzle_finished)
        self.control.connect('box-update', self.puzzle_widget.update)
        self.control.connect('title-update', self.clue_widget.update)
        self.control.connect('across-update', self.across_update)
        self.control.connect('down-update', self.down_update)
        self.control.connect('check-word-result', self.check_result)
        self.control.connect('check-puzzle-result', self.check_result)

    def do_open_file(self, fname):
        if self.clock_running:
            self.clock_button.set_active(False)
        
        if self.puzzle: self.write_puzzle()

        self.set_puzzle(Puzzle(fname))
        self.control = PuzzleController(self.puzzle)
        self.setup_controller()
        self.clue_widget.set_controller(self.control)
        self.puzzle_widget.set_puzzle(self.puzzle, self.control)

        self.load_list(ACROSS)
        self.load_list(DOWN)
        self.enable_controls(True)

        self.idle_event()

    def do_save_file(self, fname):
	self.default_loc = os.path.dirname(fname)
        self.puzzle.save(fname)

    def get_puzzle_file(self, puzzle):
        dir = os.path.expanduser('~/.crossword_puzzles')
        try: os.mkdir(dir)
        except OSError: pass

        return dir + '/' + puzzle.hashcode()

    def load_puzzle(self, fname, f):
        pp = PersistentPuzzle()
        try:
            pp.from_binary(f.read())
            
            self.puzzle.responses = pp.responses
            self.puzzle.errors = pp.errors
            self.clock_time = pp.clock
        except:
            self.notify('The saved puzzle is corrupted. It will not be used.')
            os.remove(fname)

        f.close()

    def set_puzzle(self, puzzle):
        self.clock_time = 0.0

        self.puzzle = puzzle
        if not self.puzzle: return
        
        fname = self.get_puzzle_file(puzzle)

        try: f = file(fname, 'r')
        except IOError: return
        
        opts = ['Start Over', 'Continue']
        msg = ('This puzzle has been opened before. Would you like to'
               + ' continue where you left off?')
        if self.ask(msg, opts) == 1:
            self.load_puzzle(fname, f)

    def write_puzzle(self):
        if not self.puzzle: return
        
        pp = PersistentPuzzle()
        pp.responses = self.puzzle.responses
        pp.errors = self.puzzle.errors

        if self.clock_running:
            self.clock_time += (time.time() - self.clock_start)
        pp.clock = self.clock_time

        fname = self.get_puzzle_file(self.puzzle)
        f = file(fname, 'w+')
        f.write(pp.to_binary())
        f.close()

    def exit(self):
        self.write_puzzle()
        self.write_config()
        gtk.main_quit()

    def notify(self, msg):
        dialog = gtk.MessageDialog(parent=self.win,
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

        i = 0
        for opt in opts:
            dialog.add_button(opt, i)
            i += 1
        dialog.set_default_response(i-1)

        dialog.show()
        r = dialog.run()
        dialog.destroy()

        return r

    def create_widgets(self):
        self.widgets = {}

        vbox = gtk.VBox()
        
        clue = ClueWidget(self.control)
        vbox.pack_start(clue.widget, False, False, 0)
        self.clue_widget = clue

        puzzle = PuzzleWidget(self.puzzle, self.control)
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

    def create_menubar(self):
        accel = gtk.AccelGroup()

        self.menu_items = {}

        def create_item(args, action, key, klass, active):
            item = klass(**args)
            if active: item.set_active(True)
            item.connect('activate', self.menu_selected, action)
            if key:
                item.add_accelerator('activate', accel, ord(key),
                                     gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
            return item

        def create_menu_item(label, action, key=None, klass=gtk.MenuItem,
                             active=False):
            return create_item({ 'label': label }, action, key, klass, active)

        def create_radio_item(label, action, group, active):
            return create_item({ 'label': label, 'group': group },
                               action, None, gtk.RadioMenuItem, active)

        def append(menu, name, item):
            self.menu_items[name] = item
            menu.append(item)

        menubar = gtk.MenuBar()

        file_menu = gtk.MenuItem('_File')
        menubar.append(file_menu)

        menu = gtk.Menu()
        file_menu.set_submenu(menu)

        append(menu, 'open', create_menu_item('Open', MENU_OPEN, 'O'))
        append(menu, 'save', create_menu_item('Save', MENU_SAVE, 'S'))
        append(menu, 'print', create_menu_item('Print...', MENU_PRINT, 'P'))
        append(menu, '', gtk.SeparatorMenuItem())
        append(menu, 'close', create_menu_item('Close', MENU_CLOSE, 'W'))
        append(menu, 'quit', create_menu_item('Quit', MENU_QUIT, 'Q'))

        prefs_menu = gtk.MenuItem('Preferences')
        menubar.append(prefs_menu)
            
        menu = gtk.Menu()
        prefs_menu.set_submenu(menu)
            
        append(menu, 'skip-filled',
               create_menu_item('Skip Filled', MENU_SKIP, None,
                                gtk.CheckMenuItem, self.skip_filled))
        item = create_menu_item('Word List Layout', 0)
        append(menu, 'layout', item)
        
        menu = gtk.Menu()
        item.set_submenu(menu)
        
        g = None
        i = -1
        for (name, layout) in layouts:
            item = create_radio_item(name, i, g, -(i+1) == self.layout)
            menu.append(item)
            if not g: item.set_active(True)
            g = item
            i -= 1

        self.win.add_accel_group(accel)
        return menubar

    def menu_selected(self, item, action):
        if action == MENU_QUIT:
            self.exit()
        elif action == MENU_CLOSE:
            self.exit()
        elif action == MENU_SKIP:
            self.skip_filled = not self.skip_filled
        elif action == MENU_OPEN:
            self.open_file()
        elif action == MENU_SAVE:
            self.save_file()
        elif action == MENU_PRINT:
            self.print_puzzle()
        elif action < 0:
            layout = -(action+1)
            if layout <> self.layout: self.set_layout(layout)

    def create_toolbar_item(self, label, icon, tooltip, is_toggle=False):
        if icon:
            img = gtk.Image()
            if icon[-4:] == '.png': img.set_from_file(icon)
            else: img.set_from_stock(icon, gtk.ICON_SIZE_SMALL_TOOLBAR)
        else:
            img = None

        if gtk.pygtk_version >= (2,3,90):
            if is_toggle:
                item = gtk.ToggleToolButton()
                item.set_label(label)
                item.set_icon_widget(img)
            else:
                item = gtk.ToolButton(img, label)

            item.connect('clicked', self.toolbar_event, label)
            self.toolbar.insert(item, -1)
            self.toolbar_items[label] = item
            return item
        else:
            if is_toggle:
                x = self.toolbar.append_element(gtk.TOOLBAR_CHILD_TOGGLEBUTTON,
                                                None, label, tooltip, tooltip,
                                                img, self.toolbar_event, label)
            else:
                x = self.toolbar.append_item(label, tooltip, tooltip, img,
                                             self.toolbar_event, label)
            self.toolbar_items[label] = x
            return x

    def create_separator_toolitem(self):
        if gtk.pygtk_version >= (2,3,90):
            item = gtk.SeparatorToolItem()
            item.set_draw(False)
            item.set_expand(True)
            self.toolbar.insert(item, -1)
        else:
            # I don't know how to do this
            pass

    def create_toolbar(self):
        self.toolbar_items = {}
        
        toolbar = gtk.Toolbar()
        toolbar.set_style(gtk.TOOLBAR_BOTH)
        toolbar.set_orientation(gtk.ORIENTATION_HORIZONTAL)
        self.toolbar = toolbar

        self.create_toolbar_item('Quit', gtk.STOCK_QUIT, 'Quit')
        self.create_toolbar_item('Check Word', CHECK_ICON,
                                 'Check a word')
        self.create_toolbar_item('Check Puzzle', CHECK_ALL_ICON,
                                 'Check all words in the puzzle')
        self.create_toolbar_item('Solve Word', SOLVE_ICON,
                                 'Cheat to get a word')
        self.create_separator_toolitem()
        b = self.create_toolbar_item('', TIMER_ICON,
                                     'Enable or disable the clock', True)
        self.clock_button = b
        self.idle_event()

        return toolbar

    def create_list(self, mode):
        if mode == ACROSS: label = 'Across'
        else: label = 'Down'

        tree = gtk.TreeView()
        column = gtk.TreeViewColumn(label, gtk.CellRendererText(), text=1)
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
        store = gtk.ListStore(int, str)
        i = 0
        for (n, clue) in self.control.get_clues(mode):
            self.tree_paths[mode][n] = i
            store.append((n, '%d. %s' % (n, clue)))
            i += 1

        self.trees[mode].set_model(store)

    def select_changed(self, tree, path, column, mode):
        store = tree.get_model()
        n = store.get_value(store.get_iter(path), 0)
        self.control.select_word(mode, n)
        
    def across_update(self, an):
        if self.tree_paths.has_key(ACROSS):
            selection = self.trees[ACROSS].get_selection()
            selection.select_path(self.tree_paths[ACROSS][an])
            self.trees[ACROSS].scroll_to_cell(self.tree_paths[ACROSS][an])

    def down_update(self, dn):
        if self.tree_paths.has_key(DOWN):
            selection = self.trees[DOWN].get_selection()
            selection.select_path(self.tree_paths[DOWN][dn])
            self.trees[DOWN].scroll_to_cell(self.tree_paths[DOWN][dn])

    def idle_event(self):
        t = time.time()
        if self.clock_running:
            total = int(self.clock_time + (t - self.clock_start))
        else:
            total = int(self.clock_time)
        s = time_str(total)
        sold = self.clock_button.get_label()
        if sold <> s: self.clock_button.set_label(s)

        return True

    def toolbar_event(self, widget, event):
        if event == 'Quit':
            self.exit()
        elif event == 'Check Word':
            self.control.check_word()
        elif event == 'Check Puzzle':
            self.control.check_puzzle()
        elif event == 'Solve Word':
            self.control.solve_word()
        else: # it must be the clock
            self.clock_running = not self.clock_running
            if self.clock_running:
                self.clock_start = time.time()
            else:
                self.clock_time += (time.time() - self.clock_start)

    def button_event(self, widget, event, puzzle):
        if event.type is gtk.gdk.BUTTON_PRESS:
            (x, y) = puzzle.translate_position(event.x, event.y)
            if event.button is 3: self.control.switch_mode()
            self.control.move_to(x, y)

    def key_event(self, item, event):
        name = gtk.gdk.keyval_name(event.keyval)
        
        c = self.control

        if name == 'Right': c.move(ACROSS, 1)
        elif name == 'Left': c.move(ACROSS, -1)
        elif name == 'Up': c.move(DOWN, -1)
        elif name == 'Down': c.move(DOWN, 1)
        elif name == 'BackSpace': c.back_space()
        elif name == 'Return' or name == 'Tab': c.next_word(1)
        elif name == 'ISO_Left_Tab': c.next_word(-1)
        else: return False

        return True

    def puzzle_key_event(self, item, event):
        name = gtk.gdk.keyval_name(event.keyval)
        c = self.control
        if len(name) is 1 and name.isalpha():
            c.input_char(self.skip_filled, name)
            return True
        else:
            return False

    def puzzle_finished(self):
        self.notify('You have solved the puzzle!')
        if self.clock_running:
            self.clock_button.set_active(False)

    def check_result(self, correct):
        if correct: msg = 'No mistakes found'
        else: msg = 'Incorrect.'

        self.status_bar.push(self.status_bar.get_context_id('stat'), msg)

    def open_file(self):
        def open_cb(w, open_dlg):
            self.do_open_file(open_dlg.get_filename())
            open_dlg.destroy()
        
        if gtk.pygtk_version < (2,3,90):
            dlg = gtk.FileSelection('Select a puzzle')
            dlg.connect('destroy', lambda w: dlg.destroy())
            dlg.ok_button.connect('clicked', open_cb, dlg)
            dlg.cancel_button.connect('clicked', lambda w: dlg.destroy())
            if self.default_loc: dlg.set_filename(self.default_loc + '/')
            dlg.show()
        else:
            dlg = gtk.FileChooserDialog("Open...",
                                        None,
                                        gtk.FILE_CHOOSER_ACTION_OPEN,
                                        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                         gtk.STOCK_OPEN, gtk.RESPONSE_OK))
            dlg.set_default_response(gtk.RESPONSE_OK)
            if self.default_loc: dlg.set_current_folder(self.default_loc)

            response = dlg.run()
            if response == gtk.RESPONSE_OK:
                open_cb(None, dlg)
            else:
                dlg.destroy()

    def save_file(self):
        def save_cb(w, save_dlg):
            self.do_save_file(save_dlg.get_filename())
            save_dlg.destroy()
        
        if gtk.pygtk_version < (2,3,90):
            dlg = gtk.FileSelection('Name the puzzle')
            dlg.connect('destroy', lambda w: dlg.destroy())
            dlg.ok_button.connect('clicked', save_cb, dlg)
            dlg.cancel_button.connect('clicked', lambda w: dlg.destroy())
            if self.default_loc: dlg.set_filename(self.default_loc + '/')
            dlg.show()
        else:
            dlg = gtk.FileChooserDialog("Save As...",
                                        None,
                                        gtk.FILE_CHOOSER_ACTION_SAVE,
                                        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                         gtk.STOCK_SAVE, gtk.RESPONSE_OK))
            dlg.set_default_response(gtk.RESPONSE_OK)
            if self.default_loc: dlg.set_current_folder(self.default_loc)

            response = dlg.run()
            if response == gtk.RESPONSE_OK:
                save_cb(None, dlg)
            else:
                dlg.destroy()

    def print_puzzle(self):
        if has_print:
            pr = PuzzlePrinter(self.puzzle)
            pr.print_puzzle(self.win)
        else:
            self.notify('Printing libraries are not installed. Please'
                        + ' install the Python wrapper for gnomeprint.')

    def read_config(self):
        c = ConfigParser.ConfigParser()
        c.read(os.path.expanduser('~/.crossword.cfg'))
        if c.has_section('options'):
            if c.has_option('options', 'skip_filled'):
                self.skip_filled = c.getboolean('options', 'skip_filled')
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
        c.set('options', 'layout', self.layout)
        c.set('options', 'positions', repr(self.get_layout(self.cur_layout)))
        c.set('options', 'window_size', repr(self.window_size))
        c.set('options', 'maximized', repr(self.maximized))
        c.set('options', 'default_loc', repr(self.default_loc))
        c.write(file(os.path.expanduser('~/.crossword.cfg'), 'w'))

if __name__ == '__main__':
    if len(sys.argv) <> 2:
        p = None
    else:
        p = Puzzle(sys.argv[1])
        
    w = PuzzleWindow(p)
    gtk.main()
