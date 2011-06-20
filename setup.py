#!/usr/bin/env python
#
# Written by Cameron Dale
# see LICENSE for license information
#

import sys
assert sys.version_info >= (2,3), "Install Python 2.3 or greater"
from distutils.core import setup
import xword

setup(
    name = "xword",
    version = xword.__version__,
    description = "Reads and writes crossword puzzles in the Across Lite file format",
    long_description = "Xword is a GTK+ program that works well for doing crossword puzzles in the" \
                     + " Across Lite file format used by The New York Times and others. As well as a" \
                     + " clock, it supports printing. It also auto-saves puzzles as you solve them so" \
                     + " that you can return to partially completed puzzles.",
    author = "Cameron Dale",
    author_email = "<xword-devel@lists.alioth.debian.org>",
    url = "http://alioth.debian.org/projects/xword/",
    license = "BSD",
    
    packages = ["xword"],
    scripts = ["scripts/xword"],
    package_data = {"xword": ["pixmaps/*.png"]},
    )
