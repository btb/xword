import puzzle
import config

import pygtk
pygtk.require('2.0')
import gtk
import gobject

import os.path
import datetime

DOW_SORT_ORDER = {'Mon': 0,
                  'Tue': 1,
                  'Wed': 2,
                  'Thu': 3,
                  'Fri': 4,
                  'Sat': 5,
                  'Sun': 6}

INNER_COLUMNS = 14

INNER_HASHCODE = 0
INNER_TITLE = 1
INNER_AUTHOR = 2
INNER_COPYRIGHT = 3
INNER_HSIZE = 4
INNER_VSIZE = 5
INNER_SQUARES = 6
INNER_COMPLETE = 7
INNER_ERRORS = 8
INNER_CHEATS = 9
INNER_LOCATION = 10
INNER_DATE = 11
INNER_SOURCE = 12
INNER_TITLE2 = 13

MODEL_COLOUR = 0
MODEL_DATE = 1
MODEL_DOW = 2
MODEL_SOURCE = 3
MODEL_TITLE = 4
MODEL_AUTHOR = 5
MODEL_SIZE = 6
MODEL_COMPLETE = 7
MODEL_ERRORS = 8
MODEL_CHEATS = 9
MODEL_LOCATION = 10


HEADER_NYTIMES = 'NY Times, '
AUTHOR_THINKS = 'Michael Curl'
COPYRIGHT_THINKS = 'Thinks.com'
HEADER_THINKS = 'Daily Crossword :'
#AUTHOR_CROS_SYNERGY = 'Bob Klahn'
COPYRIGHT_CROS_SYNERGY = 'CrosSynergy'
AUTHOR_MACNAMARA = 'Fred Piscop'
COPYRIGHT_MACNAMARA = 'MacNamara\'s Band'

SOURCE_NYTIMES = 'NY Times'
SOURCE_THINKS = 'Thinks.com'
SOURCE_CROS_SYNERGY = 'CrosSynergy'
SOURCE_MACNAMARA = 'MacNamara\'s Band'

def analyze_puzzle(p, f):
    if p.title.startswith(HEADER_NYTIMES):
        (date, title) = analyze_NYTimes_puzzle(p, f)
        source = SOURCE_NYTIMES
    elif p.copyright.find(COPYRIGHT_CROS_SYNERGY) >= 0:
        (date, title) = analyze_CrosSynergy_puzzle(p, f)
        source = SOURCE_CROS_SYNERGY
    elif p.copyright.find(AUTHOR_MACNAMARA) >= 0 or p.copyright.find(COPYRIGHT_MACNAMARA) >= 0:
        (date, title) = analyze_Macnamara_puzzle(p, f)
        source = SOURCE_MACNAMARA
    elif p.copyright.find(COPYRIGHT_THINKS) >= 0 or p.copyright.find(AUTHOR_THINKS) >= 0 or p.author.find(AUTHOR_THINKS) >= 0:
        (date, title) = analyze_Thinks_puzzle(p, f)
        source = SOURCE_THINKS
    else:
        date = None
        title = p.title.strip()
        source = p.copyright.strip()
        
    squares = 0
    for ((x, y), a) in p.answers.items():
        if a != '.':
            squares += 1
            
    return (squares, date, title, source)

def analyze_NYTimes_puzzle(p, f):
    title = ' '.join(p.title[len(HEADER_NYTIMES):].replace(u'\xa0', u' ').split(' ')[4:])
    notePos = title.upper().find('NOTE:')
    if notePos >= 0:
        title = title[:notePos].strip()
    bracketStart = title.find('(')
    if bracketStart >= 0:
        title = title[:bracketStart].strip()
    dateStr = ' '.join(p.title[len(HEADER_NYTIMES):].replace(u'\xa0', u' ').split(' ')[:4])
    date = datetime.datetime.strptime(dateStr, '%a, %b %d, %Y')
    return (date, title)

def analyze_CrosSynergy_puzzle(p, f):
    title = p.title.replace(u'\xa0', u' ')
    dashPos = title.find('-')
    if dashPos >= 0:
        dateStr = title[:(dashPos-1)]
        title = title[(dashPos+1):].replace('"', ' ').strip()
    date = datetime.datetime.strptime(dateStr, '%B %d, %Y')
    return (date, title)

def analyze_Macnamara_puzzle(p, f):
    title = p.title.replace(u'\xa0', u' ').strip()
    date = None
    return (date, title)

def analyze_Thinks_puzzle(p, f):
    title = p.title.replace(u'\xa0', u' ').strip()
    date = None
    if title.startswith(HEADER_THINKS):
        dateStr = title[(len(HEADER_THINKS)+1):]
        date = datetime.datetime.strptime(dateStr, '%B %d')
    try:
        date = datetime.datetime.strptime(f, 'dc1-%Y-%m-%d.puz')
    except ValueError:
        pass
    return (date, title)

class Model:
    def __init__(self, config):
        self.config = config
        self.model = None
        self.outer_model = None

    def create_model(self, update_func, done_func):
        self.model = None
        self.outer_model = None
        
        # Columns: hashcode, title, author, copyright, hsize, vsize, squares, complete, errors, cheats, location, date, source, title
        model = gtk.ListStore(str, str, str, str, int, int, int ,int, int, int, str, gobject.TYPE_PYOBJECT, str, str)
        
        modelHashes = {}
        
        scanTotal = float(len(self.config.recent_list()) + len(os.listdir(config.CONFIG_PUZZLE_DIR)))
        for dir in self.config.get_organizer_directories():
            if (os.path.exists(dir)):
                scanTotal += float(len(os.listdir(dir)))
        scanned = 0
        
        for dir in self.config.get_organizer_directories():
            if (os.path.exists(dir)):
                for f in os.listdir(dir):
                    scanned += 1
                    update_func(float(scanned) / scanTotal)
                    while gtk.events_pending():
                        gtk.main_iteration()
                    if done_func():
                        return
                        
                    fname = os.path.join(dir, f) 
                    if fname.endswith('.puz') and os.path.isfile(fname):
                        p = puzzle.Puzzle(fname)
                        hashcode = p.hashcode()
                        (squares, date, title, source) = analyze_puzzle(p, f)
                        if not date:
                            date = datetime.datetime.fromtimestamp(os.path.getmtime(fname))
                        if hashcode in modelHashes:
                            if model.iter_is_valid(modelHashes[hashcode]):
                                model.set(modelHashes[hashcode], INNER_TITLE, p.title.replace(u'\xa0', u' ').strip(),
                                          INNER_AUTHOR, p.author.replace(u'\xa0', u' ').strip(),
                                          INNER_COPYRIGHT, p.copyright.replace(u'\xa0', u' ').strip(),
                                          INNER_LOCATION, fname, INNER_DATE, date, INNER_SOURCE, source,
                                          INNER_TITLE2, title)
                            else:
                                for row in model:
                                    if row[INNER_HASHCODE] == hashcode:
                                        row[INNER_TITLE] = p.title.replace(u'\xa0', u' ').strip()
                                        row[INNER_AUTHOR] = p.author.replace(u'\xa0', u' ').strip()
                                        row[INNER_COPYRIGHT] = p.copyright.replace(u'\xa0', u' ').strip()
                                        row[INNER_LOCATION] = fname
                                        row[INNER_DATE] = date
                                        row[INNER_SOURCE] = source
                                        row[INNER_TITLE2] = title
                                        modelHashes[hashcode] = row.iter
                                        break
                        else:
                            iter = model.append()
                            model.set(iter, INNER_HASHCODE, hashcode, INNER_TITLE, p.title.replace(u'\xa0', u' ').strip(),
                                      INNER_AUTHOR, p.author.replace(u'\xa0', u' ').strip(),
                                      INNER_COPYRIGHT, p.copyright.replace(u'\xa0', u' ').strip(), INNER_HSIZE, p.width, INNER_VSIZE, p.height,
                                      INNER_SQUARES, squares, INNER_COMPLETE, 0, INNER_ERRORS, 0, INNER_CHEATS, 0, INNER_LOCATION, fname,
                                      INNER_DATE, date, INNER_SOURCE, source, INNER_TITLE2, title)
                            modelHashes[hashcode] = iter
        
        for (title, hash) in self.config.recent_list():
            scanned += 1
            update_func(float(scanned) / scanTotal)
            while gtk.events_pending():
                gtk.main_iteration()
            if done_func():
                return
            
            fname = self.config.get_recent(hash)
            if fname and os.path.exists(fname):
                p = puzzle.Puzzle(fname)
                hashcode = p.hashcode()
                if hashcode not in modelHashes:
                    (squares, date, title, source) = analyze_puzzle(p, '')
                    if not date:
                        date = datetime.datetime.fromtimestamp(os.path.getmtime(fname))
                    iter = model.append()
                    model.set(iter, INNER_HASHCODE, hashcode, INNER_TITLE, p.title, INNER_AUTHOR, p.author, INNER_COPYRIGHT, p.copyright,
                              INNER_HSIZE, p.width, INNER_VSIZE, p.height, INNER_SQUARES, squares,
                              INNER_COMPLETE, 0, INNER_ERRORS, 0, INNER_CHEATS, 0,
                              INNER_LOCATION, fname, INNER_DATE, date, INNER_SOURCE, source, INNER_TITLE2, title)
                    modelHashes[hashcode] = iter
        
        for f in os.listdir(config.CONFIG_PUZZLE_DIR):
            scanned += 1
            update_func(float(scanned) / scanTotal)
            while gtk.events_pending():
                gtk.main_iteration()
            if done_func():
                return
                
            fname = os.path.join(config.CONFIG_PUZZLE_DIR, f)
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
                            model.set(modelHashes[f], INNER_COMPLETE, complete, INNER_ERRORS, errors, INNER_CHEATS, cheats)
                        else:
                            for row in model:
                                if row[INNER_HASHCODE] == f:
                                    row[INNER_COMPLETE] = complete
                                    row[INNER_ERRORS] = errors
                                    row[INNER_CHEATS] = cheats
                                    modelHashes[f] = row.iter
                                    break
                    else:
                        iter = model.append()
                        model.set(iter, INNER_HASHCODE, f, INNER_TITLE, '', INNER_AUTHOR, '', INNER_COPYRIGHT, '',
                                  INNER_HSIZE, hsize+1, INNER_VSIZE, vsize+1, INNER_SQUARES, squares, INNER_COMPLETE, complete,
                                  INNER_ERRORS, errors, INNER_CHEATS, cheats, INNER_LOCATION, '', INNER_DATE, None, INNER_SOURCE, '', INNER_TITLE2, '')
                        modelHashes[f] = iter
        
#        self.status_bar.set_right_label('Scanned %d crossword files' % len(modelHashes))
        self.model = model
    
    def filter_model(self, model):
        def visible_func(model, iter, data=None):
            return not not model.get_value(iter, INNER_LOCATION)
            #return True
        
        def modify_func(model, iter, column, data=None):
            listmodel = model.get_model()
            row = listmodel.get(model.convert_iter_to_child_iter(iter), *range(INNER_COLUMNS))
            if column == MODEL_COLOUR:
                if not row[INNER_LOCATION]:
                    return 'red'
                elif row[INNER_SQUARES] == row[INNER_COMPLETE]:
                    return 'green'
                elif row[INNER_COMPLETE] > 0:
                    return 'blue'
                else:
                    return 'black'
            if column == MODEL_DATE:
                if row[INNER_DATE]:
                    return row[INNER_DATE].date().isoformat()
                else:
                    return ''
            elif column == MODEL_DOW:
                if row[INNER_DATE]:
                    return row[INNER_DATE].strftime('%a')
                else:
                    return ''
            elif column == MODEL_SOURCE:
                return row[INNER_SOURCE]
            elif column == MODEL_TITLE:
                return row[INNER_TITLE2]
            elif column == MODEL_AUTHOR:
                return row[INNER_AUTHOR]
            elif column == MODEL_SIZE:
                return str(row[INNER_HSIZE]) + 'x' + str(row[INNER_VSIZE])
            elif column == MODEL_COMPLETE:
                if row[INNER_SQUARES] > 0:
                    return '%0.1f%%' % (100.0 * float(row[INNER_COMPLETE]) / float(row[INNER_SQUARES]))
                else:
                    return ''
            elif column == MODEL_ERRORS:
                return row[INNER_ERRORS]
            elif column == MODEL_CHEATS:
                return row[INNER_CHEATS]
            elif column == MODEL_LOCATION:
                return row[INNER_LOCATION]
        
        modelFilter = model.filter_new()
        modelFilter.set_visible_func(visible_func)
        
        # Columns: colour, date, DOW, source, title, author, size, complete, errors, cheats, location
        modelFilter.set_modify_func((str, str, str, str, str, str, str, str, int, int, str), modify_func)
        return modelFilter

    def sort_model(self, model):
        def sort_func(model, iter1, iter2, column):
            item1 = model.get_value(iter1, column)
            item2 = model.get_value(iter2, column)
            if column == MODEL_DOW:
                if item1 in DOW_SORT_ORDER:
                    item1 = DOW_SORT_ORDER[item1]
                if item2 in DOW_SORT_ORDER:
                    item2 = DOW_SORT_ORDER[item2]
            elif column == MODEL_COMPLETE:
                if item1.endswith('%'):
                    item1 = float(item1[:(len(item1)-1)])
                if item2.endswith('%'):
                    item2 = float(item2[:(len(item2)-1)])
            if item1 < item2: return -1
            elif item2 < item1: return 1
            else: return 0
            
        modelSort = gtk.TreeModelSort(model)
        modelSort.set_sort_func(MODEL_DOW, sort_func, MODEL_DOW)
        modelSort.set_sort_func(MODEL_COMPLETE, sort_func, MODEL_COMPLETE)
        return modelSort
    
    def get_model(self):
        if not self.model:
            return None
        modelFilter = self.filter_model(self.model)
        modelSort = self.sort_model(modelFilter)
        self.outer_model = modelSort
        return modelSort
        
    def get_location(self, path):
        if not self.outer_model:
            return None
        iterSort = self.outer_model.get_iter(path)
        return self.get_location_iter(iterSort)

    def get_location_iter(self, iterSort):
        if not self.outer_model:
            return None
        modelFilter = self.outer_model.get_model()
        iterFilter = self.outer_model.convert_iter_to_child_iter(None, iterSort)
        iter = modelFilter.convert_iter_to_child_iter(iterFilter)
        location = self.model.get_value(iter, INNER_LOCATION)
        return location

    def load_puzzle(self, fname):
        pp = None
        try: f = file(fname, 'r')
        except IOError: f = None

        if f:
            try:
                pp = puzzle.PersistentPuzzle()
                pp.from_binary(f.read())
            except:
                print "Ignoring corrupt puzzle: " + fname
            finally:
                f.close()
            
        return pp

