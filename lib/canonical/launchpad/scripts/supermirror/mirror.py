import sys
import urllib
import socket
from configuration import config
from jobmanager import JobManager, LockError


def main(arguments, managerClass=JobManager, urllibOpener=urllib.urlopen):
    mymanager=managerClass()

    try:
        mymanager.lock()
    except:
        return 0

    mymanager.install()
    try:
        branchdata = urllibOpener(config.branchlistsource)
        branches = mymanager.branchStreamToBranchList(branchdata)
        if branches:
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
