# -*- coding: utf8 -*-
# -----------------------------------------------------------------------------
# Author : yongchan jeon (Kris) poucotm@gmail.com
# File   : process.py
# Create : 2017-09-25 22:30:26
# Editor : sublime text3, tab size (4)
# -----------------------------------------------------------------------------

#`protect

import traceback
import os
import threading
import subprocess


##  global functions  _________________________________________

def git_proc(cmds, callback=None, path=None):
    gt = LikeGitProcThread(cmds, path, callback)
    gt.setDaemon(True)
    gt.start()


##  class LikeGitProcThread  __________________________________

class LikeGitProcThread(threading.Thread):

    def __init__(self, cmds, path, callback):
        threading.Thread.__init__(self, name='LikeGitProcThread')
        self.cmds = cmds
        self.path = path
        self.callback = callback

    def run(self):
        info = None
        if os.name == 'nt':
            info = subprocess.STARTUPINFO()
            info.dwFlags |= subprocess.STARTF_USESTDHANDLES | subprocess.STARTF_USESHOWWINDOW
            info.wShowWindow = subprocess.SW_HIDE

        proc = None
        msgs = []
        try :
            for cmd in self.cmds:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=info, cwd=self.path, env=None)
                sout, serr = proc.communicate(timeout=30)
                sout = sout.decode().replace('\r', '')
                serr = serr.decode().replace('\r', '')
                sout = sout + serr
                msgs.append(sout)

        except Exception :
            if proc:
                proc.kill()
            print ('LIKEGIT : ERROR _____________________________________________')
            traceback.print_exc()
            print ('=============================================================')
            msgs = ['error:']

        finally :
            if self.callback is not None:
                self.callback(msgs)


#`endprotect