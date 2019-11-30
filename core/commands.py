# -*- coding: utf8 -*-
# -----------------------------------------------------------------------------
# Author : yongchan jeon (Kris) poucotm@gmail.com
# File   : commands.py
# Create : 2017-09-25 23:09:15
# Editor : sublime text3, tab size (4)
# -----------------------------------------------------------------------------

#`protect

import sublime, sublime_plugin
import re
import os
import sys
import traceback
import time
import threading
from .process import git_proc


MESSAGE = 'DO NOT DECOMPILE ---------------------------------------------------'

##  import Guna  ______________________________________________

try:
    from Guna.core.api import GunaApi
    guna_installed = True
except Exception:
    guna_installed = False


##  global variables  _________________________________________

# sublime version
STVER = int(sublime.version())

LIKEGITGRAPH = 'LikeGit - Graph'
LASTCOLORSCH = ''

##  global functions  _________________________________________
##    _________________________________________________________


def on_load():
    apply_bgcolor()
    observe_prefs()
    return


def observe_prefs(observer=None):
    prefs = sublime.load_settings("Preferences.sublime-settings")
    prefs.clear_on_change('LikeGit-prefs')
    prefs.add_on_change('LikeGit-prefs', observer or on_prefs_update)
    global LASTCOLORSCH
    if not LASTCOLORSCH:
        LASTCOLORSCH = prefs.get('color_scheme')


def on_prefs_update():
    """ To prevent unlimited calling """
    def prefs_reload():
        observe_prefs()
    observe_prefs(observer=prefs_reload)
    # call reload w/ inertial delay
    is_alive = check_thread('LikeGitPrefsThread', stop=False)
    if not is_alive:
        pthread = LikeGitPrefsThread()
        pthread.setDaemon(True)
        pthread.start()
    return


def check_thread(name, stop=False):
    is_alive = False
    for th in threading.enumerate():
        if th.name == name:
            is_alive = True
            if stop:
                th.stop()
            else:
                break
    return is_alive


def get_setting():
    return sublime.load_settings("LikeGit.sublime-settings")


##  layout  ___________________________________________________

def create_graph_group():
    """Adds a column on the right, and scales down the rest of the layout"""

    layout   = sublime.active_window().get_layout()
    cols     = layout['cols']
    cells    = layout['cells']
    last_col = len(cols) - 1
    last_row = len(layout['rows']) - 1
    lg_prefs = get_setting()
    width    = 1 - lg_prefs.get('width', 0.3)

    for i, col in enumerate(cols):
        if col > 0:
            cols[i] = col*width

    cols.append(1)
    newcell = [last_col, 0, last_col + 1, last_row]
    cells.append(newcell)
    sublime.active_window().run_command("set_layout", layout)
    return


def close_graph_group():
    """Removes the Code Map group, and scales up the rest of the layout"""

    layout    = sublime.active_window().get_layout()
    cols      = layout['cols']
    cells     = layout['cells']
    last_col  = len(cols) - 1
    map_width = cols[len(cols) - 2]

    for i, col in enumerate(cols):
        if col > 0:
            cols[i] = col/map_width

    del cols[last_col]
    del cells[len(cells) - 1]
    sublime.active_window().run_command("set_layout", layout)
    return


##  ansi color codes  _________________________________________

ansi_scope = {
    '31':'red',
    '1;31':'red_light',
    '32':'green',
    '1;32':'green_light',
    '33':'yellow',
    '1;33':'yellow_light',
    '34':'blue',
    '1;34':'blue_light',
    '35':'magenta',
    '1;35':'magenta_light',
    '36':'cyan',
    '1;36':'cyan_light',
    '37':'white',
    '1;37':'white_light',
    '0':'white_light'
}

def ansi_coloring(text):

    # find ansi regions
    ansi_regions = {}
    offst = 0
    reobj = re.compile(r'\x1b\[(?P<code>[0-9;]*?)m.*?(?=\x1b|\Z)', re.DOTALL)
    for m in reobj.finditer(text):
        try :
            acode = ansi_scope[m.group('code')]
        except:
            acode = 'white'
        cregn = sublime.Region(*m.span())
        cregn.a -= offst
        offst += len(m.group('code')) + 3
        cregn.b -= offst
        if acode in ansi_regions:
            ansi_regions[acode].append(cregn)
        else:
            ansi_regions[acode] = [cregn]

    # remove color code
    reobj = re.compile(r'\x1b\[[0-9;]*?m')
    rtext = reobj.sub('', text)

    return ansi_regions, rtext


##  git path  _________________________________________________

def find_git_path(file_name):
    """Find the closest .git path"""

    def is_work_tree(path):
        return path and os.path.exists(os.path.join(path, '.git'))

    path, name = os.path.split(file_name)
    git_dir    = ''
    work_tree  = ''
    file_rpath = name
    while path and name and name != '.git':
        if is_work_tree(path):
            git_dir   = "--git-dir=" + path + "/.git"
            work_tree = "--work-tree=" + path
            break
        else:
            path, name = os.path.split(path)
            file_rpath = name + '/' + file_rpath
    return git_dir, work_tree, file_rpath


##  get_word_cursor  __________________________________________

def get_word_cursor(view, region):
    """Get a word under cursor"""

    if region.a == region.b:
        lrgn = sublime.Region(0, 0)
        lrgn.a = 0 if region.a < 20 else (region.a - 20)
        lrgn.b = region.b
        rrgn = sublime.Region(0, 0)
        rrgn.a = region.a
        rrgn.b = view.size() if region.b + 20 > view.size() else (region.b + 20)
        matl = re.search(r'[\w]*$', view.substr(lrgn))
        matr = re.search(r'[\w]*', view.substr(rrgn))
        gets = ''
        if matl:
            gets += matl.group(0)
        if matr:
            gets += matr.group(0)
        return gets
    else:
        return view.substr(region)


##  apply_bgcolor  ____________________________________________

def get_style():
    tempv = sublime.active_window().new_file()
    style = tempv.style()
    sublime.active_window().focus_view(tempv)
    sublime.active_window().run_command('close_file')
    return style

def apply_bgcolor():
    try:
        prefs = sublime.load_settings("Preferences.sublime-settings")
        cschm = prefs.get('color_scheme')
        global LASTCOLORSCH
        if LASTCOLORSCH == cschm:
            return

        LASTCOLORSCH = cschm

        global STVER
        if STVER >= 3150:
            style = get_style()
            bgclr = style.get('background')
            fgclr = style.get('foreground')
            ivclr = style.get('invisibles')
            lhclr = style.get('line_highlight')
            slclr = style.get('selection')
            sbclr = style.get('selection_border')
        else:
            cschm = prefs.get('color_scheme')
            cstxt = str(sublime.load_resource(cschm))
            treep = plistlib.readPlistFromBytes(cstxt.encode())
            bgclr = treep['settings'][0]['settings']['background']
            fgclr = treep['settings'][0]['settings']['foreground']
            ivclr = treep['settings'][0]['settings']['invisibles']
            lhclr = treep['settings'][0]['settings']['line_highlight']
            slclr = treep['settings'][0]['settings']['selection']
            sbclr = treep['settings'][0]['settings']['selection_border']

        def set_ansi_bgcolor(hc):
            rc = int(hc[1:3], 16)
            rc = (rc - 1) if rc == 255 else (rc + 1)
            if len(hc) == 7:
                return '#{:02X}{:02X}{:02X}'.format(rc, int(hc[3:5], 16), int(hc[5:7], 16))
            elif len(hc) == 9:
                return '#{:02X}{:02X}{:02X}{:02X}'.format(rc, int(hc[3:5], 16), int(hc[5:7], 16), int(hc[7:9], 16))
            else:
                raise
                return

        def update_theme():
            themo = str(sublime.load_resource("Packages/LikeGit/theme/LikeGit.tmTheme.templ"))
            themo = themo.replace('#theme_bgcolor', bgclr)
            themo = themo.replace('#theme_fgcolor', fgclr)
            themo = themo.replace('#theme_invisibles', ivclr)
            themo = themo.replace('#theme_linehighlight', lhclr)
            themo = themo.replace('#theme_selection', slclr)
            themo = themo.replace('#theme_selborder', sbclr)
            asbgc = set_ansi_bgcolor(bgclr)
            themo = themo.replace('#ansi_bgcolor', asbgc)
            fpath = os.path.join(sublime.packages_path(), 'User')
            if not os.path.exists(fpath):
                os.makedirs(fpath)
            fpath = os.path.join(sublime.packages_path(), 'User', 'LikeGit')
            if not os.path.exists(fpath):
                os.makedirs(fpath)
            fname = os.path.join(sublime.packages_path(), 'User', 'LikeGit', 'LikeGit.tmTheme')
            with open(fname, "w", newline="") as f:
                f.write(themo)
            return

        update_theme()
    except:
        raise
    return


##  display  __________________________________________________

def disp_error(msg):
    if guna_installed:
        GunaApi.alert_message(3, ' Like Git : ' + msg, 10, 1)
    else:
        sublime.status_message(' Like Git : ' + msg)

def check_args(arg, val):
    if val == '':
        msg = arg + ' is not specified'
        disp_error(msg)
        return True
    else:
        return False


##  LikeGitPrefsThread  _______________________________________

class LikeGitPrefsThread(threading.Thread):
    """ To apply setting's change w/ some (inertial) delay """

    def __init__(self):
        threading.Thread.__init__(self, name='LikeGitPrefsThread')
        self.quit = False

    def run(self):
        try:
            time.sleep(1)
            if not self.quit:
                apply_bgcolor()
        except Exception:
            pass

    def stop(self):
        self.quit = True


##  class LikeGitGraph  _______________________________________

class LikeGitGraph(sublime_plugin.TextCommand):

    def __init__(self, view):
        sublime_plugin.TextCommand.__init__(self, view)
        self.src  = ''
        self.cmds = []
        self.git_dir = ''
        self.work_tree = ''

    def run(self, edit, **args):
        # refresh
        if self.view.name() == LIKEGITGRAPH:
            self.cmds = self.view.settings().get('likegitcmds', [])
            git_proc(self.cmds, self.on_git_graph)
        # new
        else:
            file_name = self.view.file_name()
            self.src  = file_name
            if not file_name: # or any(v.name() == LIKEGITGRAPH for v in window.views()):
                return

            # find .git path
            self.git_dir, self.work_tree, file_rpath = find_git_path(file_name)
            if self.git_dir and self.work_tree and file_rpath:
                lg_prefs = get_setting()
                max_cnts = '-' + str(lg_prefs.get('max_commits', 1000))
                self.cmds = []
                if args['target'] == 'all':
                    self.cmds.append(['git', self.git_dir, self.work_tree, 'log', '--graph', '--full-history', '--color', '--all', '--pretty=format:%x09%x1b[31m%h%x09%x1b[32m%d%x1b[0m%x20%s', max_cnts])
                else:
                    self.cmds.append(['git', self.git_dir, self.work_tree, 'log', '--graph', '--full-history', '--color', '--all', '--pretty=format:%x09%x1b[31m%h%x09%x1b[32m%d%x1b[0m%x20%s', max_cnts, '--', file_rpath])
                self.cmds.append(['git', self.git_dir, self.work_tree, 'status'])
                git_proc(self.cmds, self.on_git_graph)
        return

    def on_git_graph(self, msgs):
        self.gen_graph(msgs)

    def gen_graph(self, msgs):
        # graph view
        vl = [v for v in self.view.window().views() if v.name() == LIKEGITGRAPH]
        if len(vl) > 0:
            vl[0].settings().set('likegitsrc', self.src)
            vl[0].settings().set('likegitdir', self.git_dir)
            vl[0].settings().set('likegitworktree', self.work_tree)
            vl[0].settings().set('likegitcmd', self.cmds)
            if len(msgs) >= 2:
                vl[0].run_command("like_git_draw_graph", {"args": {'graph': msgs[0], 'status': msgs[1]}})
            elif len(msgs) >= 1:
                vl[0].run_command("like_git_draw_graph", {"args": {'graph': msgs[0], 'status': ''}})
        else:
            create_graph_group()
            graphv = sublime.active_window().new_file()
            graphv.set_name(LIKEGITGRAPH)
            graphv.settings().set('word_wrap', False)
            graphv.settings().set('gutter', False)
            graphv.settings().set('line_numbers', False)
            graphv.settings().set('likegitsrc', self.src)
            graphv.settings().set('likegitdir', self.git_dir)
            graphv.settings().set('likegitworktree', self.work_tree)
            graphv.settings().set('likegitcmd', self.cmds)
            graphv.set_scratch(True)
            graphv.settings().set("draw_white_space", "none")
            graphv.settings().set('color_scheme', 'Packages/User/LikeGit/LikeGit.tmTheme')
            if len(msgs) >= 2:
                graphv.run_command("like_git_draw_graph", {"args": {'graph': msgs[0], 'status': msgs[1]}})
            elif len(msgs) >= 1:
                graphv.run_command("like_git_draw_graph", {"args": {'graph': msgs[0], 'status': ''}})
        return


##  class LikeGitDrawGraph  ___________________________________

class LikeGitDrawGraph(sublime_plugin.TextCommand):

    def run(self, edit, args):
        self.view.set_read_only(False)
        self.view.erase(edit, sublime.Region(0, self.view.size()))
        # title
        src   = self.view.settings().get('likegitsrc', '')
        src   = os.path.basename(src)
        title = 'git repository from \"' + src + '\"\n'
        title +='─' * 500 + '\n'

        # graph
        graph = args['graph']
        graph = title + graph
        gregn, graph = ansi_coloring(graph)
        graph = graph.replace('*', u'◉')

        graph += '\n' + '─' * 500 + '\n'
        graph += args['status']

        # insert text & coloring
        self.view.insert(edit, 0, graph)
        for scope, regions in gregn.items():
            self.view.add_regions(scope, regions, scope, '', sublime.DRAW_NO_OUTLINE | sublime.PERSISTENT)

        self.view.set_read_only(True)
        return


##  LikeGitCheckOut  __________________________________________

class LikeGitCheckout(sublime_plugin.TextCommand):

    def run(self, edit):
        if self.view.name() != LIKEGITGRAPH:
            return

        gitdir   = self.view.settings().get('likegitdir', '')
        if check_args('git directory', gitdir):
            return
        worktr   = self.view.settings().get('likegitworktree', '')
        if check_args('work tree', worktr):
            return
        graphcmd = self.view.settings().get('likegitcmd', '')
        try :
            commit = get_word_cursor(self.view, self.view.sel()[0])
        except :
            check_args('commit', '')
            return
        if check_args('commit', commit):
            return
        if commit:
            cmds  = []
            cmds.append(['git', gitdir, worktr, 'checkout', commit])
            cmds.append(graphcmd[0])
            cmds.append(graphcmd[1])
            git_proc(cmds, self.on_git_checkout)

    def on_git_checkout(self, msgs):
        self.view.run_command("like_git_draw_graph", {"args": {'graph': msgs[1], 'status': msgs[0]}})

    def is_visible(self):
        return self.view.name() == LIKEGITGRAPH


##  LikeGitDiff  ______________________________________________

class LikeGitDiff(sublime_plugin.TextCommand):

    def run(self, edit, **args):
        if self.view.name() != LIKEGITGRAPH:
            return

        gitdir  = self.view.settings().get('likegitdir', '')
        if check_args('git directory', gitdir):
            return
        worktr  = self.view.settings().get('likegitworktree', '')
        if check_args('work tree', worktr):
            return
        try :
            cmds = []
            if args['target'] == 'all':
                try :
                    commit0 = get_word_cursor(self.view, self.view.sel()[0])
                except :
                    check_args('commit0', '')
                    return
                if check_args('commit0', commit0):
                    return
                try :
                    commit1 = get_word_cursor(self.view, self.view.sel()[1])
                except :
                    check_args('commit1', '')
                    return
                if check_args('commit1', commit1):
                    return
                if commit0 and commit1:
                    cmds.append(['git', gitdir, worktr, 'difftool', '--dir-diff', commit0, commit1])
                    git_proc(cmds, self.on_git_diff)
            elif args['target'] == 'stash':
                cmds.append(['git', gitdir, worktr, 'difftool'])
                git_proc(cmds, self.on_git_diff)
        except :
            pass

    def on_git_diff(self, msg):
        return

    def is_visible(self):
        return self.view.name() == LIKEGITGRAPH


##  LikeGitBash  ______________________________________________

class LikeGitBash(sublime_plugin.TextCommand):

    def run(self, edit, **args):
        if self.view.name() != LIKEGITGRAPH:
            return

        worktr = self.view.settings().get('likegitworktree', '')
        worktr = worktr.replace(r'--work-tree=', '')
        if check_args('work tree', worktr):
            return
        try :
            cmds  = []
            prefs = sublime.load_settings("LikeGit.sublime-settings")
            gbash = prefs.get('git-bash')
            if os.name == 'nt':
                term_ = gbash.get('windows')
            elif sys.platform == 'darwin':
                term_ = gbash.get('osx')
                if term_ == 'osx/terminal.sh':
                    term_ = os.path.join(sublime.packages_path(), 'LikeGit/osx/terminal.sh')
                    if not os.access(term_, os.X_OK):
                        os.chmod(term_, 0o755)
            else:
                term_ = gbash.get('linux')

            cmds.append(term_)
            git_proc(cmds, path=worktr)
        except :
            print ('LIKEGIT : ERROR _____________________________________________')
            traceback.print_exc()
            print ('=============================================================')

    def is_visible(self):
        return self.view.name() == LIKEGITGRAPH


##  LikeGitListener  __________________________________________

class LikeGitListener(sublime_plugin.EventListener):

    def on_close(self, view):
        if view.name() == LIKEGITGRAPH:
            close_graph_group()
        return


#`endprotect