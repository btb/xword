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

import puzzle
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
import subprocess
import datetime

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

ACROSS = puzzle.ACROSS
DOWN = puzzle.DOWN

ui_description = '''
<ui>
  <menubar name="Menubar">
    <menu action="MenuFile">
      <menuitem action="Open"/>
      <menuitem action="Refresh"/>
      <menu action="MenuRecent">
        <menuitem action="Recent0"/>
        <menuitem action="Recent1"/>
        <menuitem action="Recent2"/>
        <menuitem action="Recent3"/>
        <menuitem action="Recent4"/>
      </menu>
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
      <menuitem action="About"/>
    </menu>
  </menubar>
  <toolbar name="Toolbar">
    <toolitem action="Open"/>
    <toolitem action="Refresh"/>
    <toolitem action="Print"/>
  </toolbar>
</ui>
'''

def time_str(t):
    total = int(t)
    secs = total % 60
    mins = (total / 60) % 60
    hrs = (total / 3600)
    return "%d:%02d:%02d" % (hrs, mins, secs)

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

class OrganizerWindow:
    def __init__(self):
        self.setup_config_dir()
        self.done = False
        gobject.idle_add(self.init)
        
    def init(self):
        store = puzzle.PuzzleStore(config_path('crossword-recent'),
                                   config_path('crossword-recent-list'))
        self.puzzle_store = store
        self.status_bar = StatusBar()
        
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.win = window
        def destroy(widget, data=None):
            self.done = True
            self.exit()
        handler = window.connect('destroy', destroy)
        
        pbar = self.create_progress_bar(window)
        
        model = self.create_model(store, pbar.set_fraction)

        if self.done:
            return
        
        self.win.handler_disconnect(handler)
        self.win.destroy()
        
        self.skip_filled = False
        self.start_timer = False
        self.layout = 0
        self.window_size = (900, 600)
        self.maximized = False
        self.positions = 'puzzle'
        self.default_loc = None

        win = gtk.Window()
        self.win = win
        self.handler = win.connect('destroy', lambda w: self.exit())
        win.connect('size-allocate', self.resize_window)
        win.connect('window-state-event', self.state_event)

        self.read_config()

        win.resize(self.window_size[0], self.window_size[1])
        if self.maximized: win.maximize()
        
        mainbox = gtk.VBox()
        win.add(mainbox)
        mainbox = mainbox

        self.create_ui()
        mainbox.pack_start(self.menubar, False, False, 0)
        mainbox.pack_start(self.toolbar, False, False, 0)

        win.set_title('Xword Organizer')

        scroll = gtk.ScrolledWindow()
        mainbox.pack_start(scroll, True, True, 0)
        
        modelFilter = self.filter_model(model)
        modelSort = self.sort_model(modelFilter)
        tree = self.create_list_view(modelSort)
        scroll.add(tree)
        self.tree = tree

        mainbox.pack_start(self.status_bar.frame, False, False, 0)

        self.enable_controls(False, False)

        win.show_all()
        self.status_bar.set_status('Double-click a crossword to open it')

        tree.grab_focus()

    def create_progress_bar(self, window):
        window.set_position(gtk.WIN_POS_CENTER)
        window.set_resizable(True)

        window.set_title("Scanning Crossword Files")
        window.set_border_width(0)

        vbox = gtk.VBox(False, 5)
        vbox.set_border_width(10)
        window.add(vbox)
        vbox.show()
  
        # Create the ProgressBar
        pbar = gtk.ProgressBar()
        pbar.set_size_request(300, -1)
        vbox.pack_start(pbar, False, False, 5)
        pbar.show()

        separator = gtk.HSeparator()
        vbox.pack_start(separator, False, False, 0)
        separator.show()

        # Create a centering alignment object
        align = gtk.Alignment(0.5, 0.5, 0, 0)
        vbox.pack_start(align, False, False, 5)
        
        # Add a button to exit the program
        button = gtk.Button("Cancel")
        button.connect_object("clicked", gtk.Widget.destroy, window)
        align.add(button)
        align.show()

        # This makes it so the button is the default.
        button.set_flags(gtk.CAN_DEFAULT)

        # This grabs this button to be the default button. Simply hitting
        # the "Enter" key will cause this button to activate.
        button.grab_default()
        button.show()

        window.show()
        
        return pbar
        
    def create_model(self, store, update_func):
        # Columns: hashcode, title, author, copyright, hsize, vsize, squares, complete, errors, cheats, location, date, source, title
        model = gtk.ListStore(str, str, str, str, int, int, int ,int, int, int, str, gobject.TYPE_PYOBJECT, str, str)
        
        modelHashes = {}
        
        dir = '/home/cdale/doc/NYTxword'
        
        scanTotal = float(len(os.listdir(dir)) + len(store.recent_list()) + len(os.listdir(config_path('crossword_puzzles'))))
        scanned = 0
        
        for f in os.listdir(dir):
            scanned += 1
            update_func(float(scanned) / scanTotal)
            while gtk.events_pending():
                gtk.main_iteration()
            if self.done:
                return
                
            fname = os.path.join(dir, f) 
            if fname.endswith('.puz') and os.path.isfile(fname):
                p = puzzle.Puzzle(fname)
                hashcode = p.hashcode()
                squares = 0
                date = None
                title = ''
                HEADER_NYTIMES = 'NY Times, '
                source = 'Unknown'
                if p.title.startswith(HEADER_NYTIMES):
                    source = 'NY Times'
                    title = ' '.join(p.title[len(HEADER_NYTIMES):].replace(u'\xa0', u' ').split(' ')[4:])
                    notePos = title.upper().find('NOTE:')
                    if notePos >= 0:
                        title = title[:notePos].strip()
                    bracketStart = title.find('(')
                    if bracketStart >= 0:
                        title = title[:bracketStart].strip()
                    dateStr = ' '.join(p.title[len(HEADER_NYTIMES):].replace(u'\xa0', u' ').split(' ')[:4])
                    date = datetime.datetime.strptime(dateStr, '%a, %b %d, %Y')
                for ((x, y), a) in p.answers.items():
                    if a != '.':
                        squares += 1
                if hashcode in modelHashes:
                    if model.iter_is_valid(modelHashes[hashcode]):
                        model.set(modelHashes[hashcode], 1, p.title, 2, p.author, 3, p.copyright, 10, fname, 11, date, 12, source, 13, title)
                    else:
                        for row in model:
                            if row[0] == hashcode:
                                row[1] = p.title.replace(u'\xa0', u' ').strip()
                                row[2] = p.author.replace(u'\xa0', u' ').strip()
                                row[3] = p.copyright.replace(u'\xa0', u' ').strip()
                                row[10] = fname
                                row[11] = date
                                row[12] = source
                                row[13] = title
                                modelHashes[hashcode] = row.iter
                                break
                else:
                    iter = model.append([hashcode, p.title, p.author, p.copyright, p.width, p.height, squares, 0, 0, 0, fname, date, source, title])
                    modelHashes[hashcode] = iter
        
        for (title, hash) in store.recent_list():
            scanned += 1
            update_func(float(scanned) / scanTotal)
            while gtk.events_pending():
                gtk.main_iteration()
            if self.done:
                return
            
            fname = store.get_recent(hash)
            if fname and os.path.exists(fname):
                p = puzzle.Puzzle(fname)
                hashcode = p.hashcode()
                if hashcode not in modelHashes:
                    squares = 0
                    for ((x, y), a) in p.answers.items():
                        if a != '.':
                            squares += 1
                    iter = model.append([hashcode, p.title, p.author, p.copyright, p.width, p.height, squares, 0, 0, 0, fname, None, '', ''])
                    modelHashes[hashcode] = iter
        
        dir = config_path('crossword_puzzles')
        for f in os.listdir(dir):
            scanned += 1
            update_func(float(scanned) / scanTotal)
            while gtk.events_pending():
                gtk.main_iteration()
            if self.done:
                return
                
            fname = os.path.join(dir, f)
            if os.path.isfile(fname):
                pp = self.load_puzzle(fname)
                if pp:
                    hsize = 0
                    vsize = 0
                    squares = 0
                    complete = 0
                    errors = 0
                    cheats = 0
                    for ((x, y), r) in pp.responses.items():
                        if x > hsize: hsize = x
                        if y > vsize: vsize = y
                        if r != '.':
                            squares += 1
                            if r != '':
                                complete += 1
                    for ((x, y), e) in pp.errors.items():
                        if e == puzzle.MISTAKE or e == puzzle.FIXED_MISTAKE:
                            errors += 1
                        if e == puzzle.CHEAT:
                            cheats += 1
                    if f in modelHashes:
                        if model.iter_is_valid(modelHashes[f]):
                            model.set(modelHashes[f], 7, complete, 8, errors, 9, cheats)
                        else:
                            for row in model:
                                if row[0] == f:
                                    row[7] = complete
                                    row[8] = errors
                                    row[9] = cheats
                                    modelHashes[f] = row.iter
                                    break
                    else:
                        iter = model.append([f, '', '', '', hsize+1, vsize+1, squares, complete, errors, cheats, '', None, '', ''])
                        modelHashes[f] = iter
        
        self.status_bar.set_right_label('Scanned %d crossword files' % len(modelHashes))
        return model
    
    def filter_model(self, model):
        def visible_func(model, iter, data=None):
            #return not not model.get_value(iter, 10)
            return True
        
        def modify_func(model, iter, column, data=None):
            listmodel = model.get_model()
            row = listmodel.get(model.convert_iter_to_child_iter(iter), 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13)
            if column == 0:
                if not row[10]:
                    return 'red'
                elif row[6] == row[7]:
                    return 'green'
                elif row[7] > 0:
                    return 'blue'
                else:
                    return 'black'
            if column == 1:
                if row[11]:
                    return row[11].date().isoformat()
                else:
                    return ''
            elif column == 2:
                if row[11]:
                    return row[11].strftime('%a')
                else:
                    return ''
            elif column == 3:
                return row[12]
            elif column == 4:
                return row[13]
            elif column == 5:
                return row[2]
            elif column == 6:
                return str(row[4]) + 'x' + str(row[5])
            elif column == 7:
                return '%0.1f%%' % (100.0 * float(row[7]) / float(row[6]))
            elif column == 8:
                return row[8]
            elif column == 9:
                return row[9]
        
        modelFilter = model.filter_new()
        modelFilter.set_visible_func(visible_func)
        modelFilter.set_modify_func((str, str, str, str, str, str, str, str, int, int), modify_func)
        return modelFilter

    def sort_model(self, model):
        dow = {'Mon': 0,
               'Tue': 1,
               'Wed': 2,
               'Thu': 3,
               'Fri': 4,
               'Sat': 5,
               'Sun': 6}
        def sort_func(model, iter1, iter2, data):
            item1 = model.get_value(iter1, data)
            item2 = model.get_value(iter2, data)
            if data == 2:
                if item1 in dow:
                    item1 = dow[item1]
                if item2 in dow:
                    item2 = dow[item2]
            if item1 < item2: return -1
            elif item2 < item1: return 1
            else: return 0
            
        modelSort = gtk.TreeModelSort(model)
        modelSort.set_sort_func(2, sort_func, 2)
        modelSort.set_sort_column_id(1, gtk.SORT_DESCENDING)
        return modelSort
        
    def create_list_view(self, model):
        tree = gtk.TreeView(model)
        tree.set_headers_clickable(True)
        tree.set_rules_hint(True)
        
        def addColumn(name, columnId):
            cell = gtk.CellRendererText()
            column = gtk.TreeViewColumn(name, cell, text=columnId, foreground=0)
            column.set_sort_column_id(columnId)
            tree.append_column(column)
        
        addColumn('Date', 1)
        addColumn('Weekday', 2)
        addColumn('Source', 3)
        addColumn('Title', 4)
        addColumn('Author', 5)
        addColumn('Size', 6)
        addColumn('Complete', 7)
        addColumn('Errors', 8)
        addColumn('Cheats', 9)

        tree.connect('row-activated', self.row_activated)
        
        return tree
        
    def row_activated(self, treeview, path, view_column, data=None):
        modelSort = treeview.get_model()
        iterSort = modelSort.get_iter(path)
        modelFilter = modelSort.get_model()
        iterFilter = modelSort.convert_iter_to_child_iter(None, iterSort)
        model = modelFilter.get_model()
        iter = modelFilter.convert_iter_to_child_iter(iterFilter)
        location = model.get_value(iter, 10)
        self.launch_puzzle(location)

    def launch_puzzle(self, location):
        p = subprocess.Popen([sys.argv[0], location])
        
    def enable_controls(self, enabled, locked):
        def enable(a, x):
            action = self.actiongroup.get_action(a)
            action.set_sensitive(x)

        enable('PageSetup', enabled)
        enable('Print', enabled)

    def open_recent(self, index):
        (title, hashcode) = self.puzzle_store.recent_list()[index]
        fname = self.puzzle_store.get_recent(hashcode)
        self.launch_puzzle(fname)

    def get_puzzle_file(self, puzzle):
        dir = config_path('crossword_puzzles')
        return os.path.join(dir, puzzle.hashcode())

    def load_puzzle(self, fname):
        pp = None
        try: f = file(fname, 'r')
        except IOError: f = None

        if f:
            try:
                pp = puzzle.PersistentPuzzle()
                pp.from_binary(f.read())
            except:
                self.notify('The saved puzzle is corrupted. It will not be used: ' + fname)
                #os.remove(fname)

            f.close()
            
        return pp

    def exit(self):
        #self.write_config()
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
            mk('Refresh', gtk.STOCK_REFRESH),
            mk('MenuRecent', None, 'Open recent'),
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
                  'Start timer automatically', self.start_timer)
            ])            

        ui.insert_action_group(actiongroup, 0)
        ui.add_ui_from_string(ui_description)

        self.update_recent_menu()

        self.menubar = ui.get_widget('/Menubar')
        self.toolbar = ui.get_widget('/Toolbar')

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
        elif name == 'Refresh':
            self.refresh_model()
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
            self.launch_puzzle(fname)
        else:
            dlg.destroy()
    
    def refresh_model(self):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        def destroy(widget, data=None):
            self.done = True
        handler = window.connect('destroy', destroy)
        
        pbar = self.create_progress_bar(window)
        
        self.done = False
        model = self.create_model(self.puzzle_store, pbar.set_fraction)

        if not self.done:
            window.destroy()
            modelFilter = self.filter_model(model)
            modelSort = self.sort_model(modelFilter)
            self.tree.set_model(modelSort)

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
        c.set('options', 'positions', repr(self.positions))
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
    w = OrganizeWindow(fname)
    gtk.main()
