#!/usr/bin/python

from xword.main import PuzzleWindow

import gtk
import sys

if __name__ == '__main__':
    if len(sys.argv) <> 2:
        p = None
    else:
        p = Puzzle(sys.argv[1])
        
    w = PuzzleWindow(p)
    gtk.main()
