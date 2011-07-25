import puzzle
import printing
import model
import config
import __init__

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
import subprocess

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
    <menu action="MenuPreferences">
      <menuitem action="ChooseDirectory"/>
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
        self.done = False
        gobject.idle_add(self.init)
        
    def init(self):
        self.config = config.XwordConfig()
        self.status_bar = StatusBar()
        
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.win = window
        def destroy(widget, data=None):
            self.done = True
            self.exit()
        handler = window.connect('destroy', destroy)
        
        if not self.config.get_organizer_directories():
            opts = ['Skip', 'Configure']
            msg = ('You have not configured a puzzle directory to scan for puzzle'
                   + ' files. Would you like to configure it now?')
            if self.ask(msg, opts) == 1:
                self.choose_directory(False)
        
        pbar = self.create_progress_bar(window)
        
        self.model = model.Model(self.config)
        self.model.create_model(pbar.set_fraction, self.is_done)

        if self.done:
            return
        
        self.win.handler_disconnect(handler)
        self.win.destroy()
        
        self.organizer_maximized = self.config.get_organizer_maximized()
        
        win = gtk.Window()
        self.win = win
        self.handler = win.connect('destroy', destroy)
        win.connect('size-allocate', self.resize_window)
        win.connect('window-state-event', self.state_event)

        organizer_window_size = self.config.get_organizer_window_size()
        win.resize(organizer_window_size[0], organizer_window_size[1])
        if self.organizer_maximized: win.maximize()
        
        mainbox = gtk.VBox()
        win.add(mainbox)
        mainbox = mainbox

        self.create_ui()
        mainbox.pack_start(self.menubar, False, False, 0)
        mainbox.pack_start(self.toolbar, False, False, 0)

        win.set_title('Xword Organizer')

        scroll = gtk.ScrolledWindow()
        mainbox.pack_start(scroll, True, True, 0)
        
        modelSort = self.model.get_model()
        modelSort.set_sort_column_id(model.MODEL_DATE, gtk.SORT_DESCENDING)
        tree = self.create_list_view(modelSort)
        scroll.add(tree)
        self.tree = tree

        mainbox.pack_start(self.status_bar.frame, False, False, 0)

        self.enable_controls(False)

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
        
    def is_done(self):
        return self.done
    
    def create_list_view(self, modelSort):
        tree = gtk.TreeView(modelSort)
        tree.set_headers_clickable(True)
        tree.set_rules_hint(True)
        
        def addColumn(name, columnId):
            cell = gtk.CellRendererText()
            column = gtk.TreeViewColumn(name, cell, text=columnId, foreground=model.MODEL_COLOUR)
            column.set_sort_column_id(columnId)
            tree.append_column(column)
        
        addColumn('Date', model.MODEL_DATE)
        addColumn('Weekday', model.MODEL_DOW)
        addColumn('Source', model.MODEL_SOURCE)
        addColumn('Title', model.MODEL_TITLE)
        addColumn('Author', model.MODEL_AUTHOR)
        addColumn('Size', model.MODEL_SIZE)
        addColumn('Complete', model.MODEL_COMPLETE)
        addColumn('Errors', model.MODEL_ERRORS)
        addColumn('Cheats', model.MODEL_CHEATS)
        addColumn('Location', model.MODEL_LOCATION)

        tree.connect('row-activated', self.row_activated)
        tree.connect('cursor-changed', self.cursor_changed)
        
        return tree
        
    def refresh_model(self):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        def destroy(widget, data=None):
            self.done = True
        handler = window.connect('destroy', destroy)
        
        pbar = self.create_progress_bar(window)
        
        self.done = False
        self.model.create_model(pbar.set_fraction, self.is_done)

        if not self.done:
            window.destroy()
            modelSort = self.model.get_model()
            modelSort.set_sort_column_id(model.MODEL_DATE, gtk.SORT_DESCENDING)
            self.tree.set_model(modelSort)

    def row_activated(self, treeview, path, view_column, data=None):
        location = self.model.get_location(path)
        self.launch_puzzle(location)
        
    def cursor_changed(self, treeview, data=None):
        selection = self.tree.get_selection()
        (model, iter) = selection.get_selected()
        if iter:
            self.enable_controls(True)

    def launch_puzzle(self, location):
        p = subprocess.Popen([sys.argv[0], location])
        
    def enable_controls(self, enabled):
        def enable(a, x):
            action = self.actiongroup.get_action(a)
            action.set_sensitive(x)

        enable('PageSetup', enabled)
        enable('Print', enabled)

    def open_recent(self, index):
        (title, hashcode) = self.config.recent_list()[index]
        fname = self.config.get_recent(hashcode)
        self.launch_puzzle(fname)

    def exit(self):
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
        dialog.set_version(__init__.__version__)
        dialog.set_license(__init__.__license__)
        dialog.set_authors(
            ['Cameron Dale <camrdale@gmail.com>\n' +
             'Bill McCloskey <bill.mccloskey@gmail.com>\n' +
             'Maemo Port: Bradley Bell <bradleyb@u.washington.edu>\n' +
             'and Terrence Fleury <terrencegf@gmail.com>'])
        dialog.set_website('http://x-word.org')
        dialog.set_website_label('x-word.org')

        dialog.connect('response', lambda *args: dialog.destroy())
        dialog.show()

    def state_event(self, w, event):
        state = int(event.new_window_state)
        organizer_maximized = (state & gtk.gdk.WINDOW_STATE_MAXIMIZED) <> 0
        if (self.organizer_maximized != organizer_maximized):
            self.organizer_maximized = organizer_maximized
            self.config.set_organizer_maximized(organizer_maximized) 

    def resize_window(self, widget, allocation):
        if not self.organizer_maximized:
            self.config.set_organizer_window_size(self.win.get_size())

    def update_recent_menu(self):
        recent = self.config.recent_list()
        for (i, (title, hashcode)) in enumerate(recent):
            action = self.actiongroup.get_action('Recent%d' % i)
            action.set_sensitive(True)
            action.set_property('label', title)

    def create_ui(self):
        ui = gtk.UIManager()
        
        accelgroup = ui.get_accel_group()
        self.win.add_accel_group(accelgroup)

        actiongroup = gtk.ActionGroup('XwordOrganizerActions')
        self.actiongroup = actiongroup

        def mk(action, stock_id, label=None, tooltip=None):
            return (action, stock_id, label, None,
                    tooltip, self.action_callback)

        actiongroup.add_actions([
            mk('MenuFile', None, '_File'),
            mk('Open', gtk.STOCK_OPEN, tooltip='Open a puzzle file'),
            mk('Refresh', gtk.STOCK_REFRESH, tooltip='Refresh the scanned crossword files'),
            mk('MenuRecent', None, 'Open recent'),
            mk('PageSetup', None, 'Page setup...'),
            mk('Print', gtk.STOCK_PRINT, tooltip='Print the selected puzzle'),
            mk('Close', gtk.STOCK_CLOSE),
            mk('Quit', gtk.STOCK_QUIT),

            mk('Recent0', None, 'No recent item'),
            mk('Recent1', None, 'No recent item'),
            mk('Recent2', None, 'No recent item'),
            mk('Recent3', None, 'No recent item'),
            mk('Recent4', None, 'No recent item'),

            mk('MenuPreferences', None, 'Preferences'),
            mk('ChooseDirectory', None, 'Puzzle Directory...'),

            mk('MenuHelp', None, '_Help'),
            mk('About', None, 'About'),
            ])

        def mktog(action, stock_id, label, active):
            return (action, stock_id, label,
                    None, None, self.action_callback, active)

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
        elif name == 'ChooseDirectory':
            self.choose_directory()
        elif name.startswith('Recent'):
            index = int(name[len('Recent'):])
            self.open_recent(index)

    def open_file(self):
        dlg = gtk.FileChooserDialog("Open...",
                                    None,
                                    gtk.FILE_CHOOSER_ACTION_OPEN,
                                    (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                     gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dlg.set_default_response(gtk.RESPONSE_OK)
        default_loc = self.config.get_default_loc()
        if default_loc: dlg.set_current_folder(default_loc)

        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            fname = dlg.get_filename()
            dlg.destroy()
            self.launch_puzzle(fname)
        else:
            dlg.destroy()
    
    def choose_directory(self, refresh=True):
        dlg = gtk.FileChooserDialog("Choose Puzzle Directory to Scan...",
                                    None,
                                    gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                    (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                     gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dlg.set_default_response(gtk.RESPONSE_OK)
        default_loc = self.config.get_default_loc()
        if len(self.config.get_organizer_directories()) > 0:
            default_loc = self.config.get_organizer_directories()[0]
        if default_loc: dlg.set_current_folder(default_loc)

        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            dir = dlg.get_filename()
            dlg.destroy()
            self.config.set_organizer_directories([dir])
            if refresh:
                self.refresh_model()
        else:
            dlg.destroy()
    
    def page_setup(self):
        if has_print:
            selection = self.tree.get_selection()
            (model, iter) = selection.get_selected()
            location = self.model.get_location_iter(iter)
            puz = puzzle.Puzzle(location)
            pr = printing.PuzzlePrinter(puz)
            pr.do_page_setup(self.win)
        else:
            self.notify('Printing support is not available (need GTK 2.10+).')

    def print_puzzle(self):
        if has_print:
            selection = self.tree.get_selection()
            (model, iter) = selection.get_selected()
            location = self.model.get_location_iter(iter)
            puz = puzzle.Puzzle(location)
            pr = printing.PuzzlePrinter(puz)
            pr.print_puzzle(self.win)
        else:
            self.notify('Printing support is not available (need GTK 2.10+).')

if __name__ == '__main__':
    w = OrganizerWindow()
    gtk.main()
