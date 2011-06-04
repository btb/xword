#!/usr/bin/env python

from xword.main import MainWindow
from xword.organizer import OrganizerWindow
 
import sys
import gtk

if __name__ == '__main__':
    if len(sys.argv) <> 2: fname = None
    else: fname = sys.argv[1]
        
    if fname:
        w = MainWindow(fname)
    else:
        w = OrganizerWindow()
    gtk.main()

