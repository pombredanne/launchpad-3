# Copyright 2006 Canonical Ltd.  All rights reserved.

import socket
import sys
import urllib

from canonical.config import config
from canonical.launchpad.scripts.supermirror.jobmanager import JobManager

config.supermirror.branchlistsource = 'http://foo.com/baz'

def mirror(managerClass=JobManager, lockfile=config.supermirror.masterlock,
           urllibOpener=urllib.urlopen):
    """Mirror the given branches into the directory specified in
    config.supermirror.branchesdest.
    
    branches must be a list of canonical.launchpad.database.branch.Branch
    objects.
    """
    mymanager = managerClass()
    try:
        mymanager.lock()
    except:
        return 0

    mymanager.install()
    try:
        branchdata = urllibOpener(config.supermirror.branchlistsource)
        branches = mymanager.branchStreamToBranchList(branchdata)
        for branch in branches:
            mymanager.add(branch)
        mymanager.run()
        mymanager.uninstall()
        mymanager.unlock()
    except socket.error:
        print >> sys.stderr,  "Launchpad is unreachable" 
        mymanager.uninstall()
        mymanager.unlock()
    except:
        mymanager.uninstall()
        mymanager.unlock()
        raise
    return 0

