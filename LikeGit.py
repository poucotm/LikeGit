# -*- coding: utf8 -*-
# -----------------------------------------------------------------------------
# Author : yongchan jeon (Kris) poucotm@gmail.com
# File   : LikeGit.py
# Create : 2019-01-17 23:44:34
# Editor : sublime text3, tab size (4)
# -----------------------------------------------------------------------------

import sublime, sublime_plugin
import sys, imp
import traceback

try:
    # reload
    mods = ['LikeGit.core.process', 'LikeGit.core.commands']
    for mod in list(sys.modules):
        if any(mod == m for m in mods):
            imp.reload(sys.modules[mod])
    # import
    from .core import commands
    from .core import process
    from .core.commands import (LikeGitGraph, LikeGitDrawGraph, LikeGitCheckout, LikeGitDiff, LikeGitListener)
    import_ok = True
except Exception:
    print ('LIKEGIT : ERROR _____________________________________________')
    traceback.print_exc()
    print ('=============================================================')
    import_ok = False


##  plugin_loaded  ____________________________________________

def plugin_loaded():

    # import
    if not import_ok:
        sublime.status_message("* LikeGit : Error in importing sub-modules. Please, see the trace-back message in Sublime console")
        return

    commands.on_load()