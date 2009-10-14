#!/usr/bin/env python

from xword.main import MainWindow
 
import sys
import gtk

if __name__ == '__main__':
    if len(sys.argv) <> 2: fname = None
    else: fname = sys.argv[1]
        
    w = MainWindow(fname)
    gtk.main()

