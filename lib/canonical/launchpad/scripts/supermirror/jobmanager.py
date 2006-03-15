import signal
import os

from supermirror.bzr_5_6 import BZR_5_6
from supermirror import lockfile
from configuration import config
from branchtargeter import branchtarget
from supermirror.branchfactory import BranchFactory

class JobManager:
    """Schedule and manage the mirroring of branches.
    
    The jobmanager is responsible for organizing the mirroring of all
    branches.
    """

    def __init__(self):
        self.jobs = []
        self.jobswaiting = 0
        self.hemlock = False
        self.actualLock = None
        # dictonary of queues
    
    def die(self):
        """Tell the jobmanager to quit as soon as is safe.
        
        This method is most useful in a threaded scenario. Calling this
        method will allow the job manager to finish up mirrors that are
        actively being performed. Branches that have not been mirrored yet
        will not be started.
        """
        self.hemlock = True

    def install (self):
        """Tell JobManager to start the signal handler
        
        The JobManager can accept signals from sysadmins to die. This
        method installs the signal handler for this purpose
        """
        self.origSignal = signal.signal(JobManagerController.killSignal,
                                        self.killRecieved)

    def uninstall (self):
        """Tell JobManager to uninstall the signal handler"""
        signal.signal(JobManagerController.killSignal, self.origSignal)

    def add (self, target):
        """Add a job to the JobManager

        The target should be an object that has a run method. The
        jobmanager will append the job to its internal list of jobs to run.
        """
        # XXX This may not be necessary. Regardless, it would be better to
        # assert if target is None. Either way, update the test cases. I
        # think I threw this in to deal with lines that were slipping
        # through the branch targeter? -jblack 2006-03-13
        if target is not None:
           self.jobs.append(target)
           self.jobswaiting += 1

    def run(self):
        """Run all jobs registered with the JobManager"""
        for obj in self.jobs:
            obj.run()
            self.jobswaiting -= 1

    def killRecieved(self, signal_number, stack_frame):
        """Method for signal handler to tell JobManager to die"""
        # XXX This is trivial to implement by hooking up to self.die().
        # However, its not implemented yet as there is no test case written
        # for it yet. -jblack 2006-03-13
        raise NotImplementedError

    def branchStreamToBranchList(self, inputstream):
        """Convert a stream of branch URLS to list of branch objects.
        
        This function takes a file handle associated with a text file of
        the form:
            
            LAUNCHPAD_ID URL_FOR_BRANCH
            ...
            LAUNCHPAD_ID URL_FOR_BRANCH

        This series of urls is converted into a python list of branch
        objects of the appropriate type.
        """
        branches = []
        branchfactory = BranchFactory()
        destination = config.branchesdest
        for line in inputstream.readlines():
            (branchnum, branchsrc) = line.split(" ")
            branchsrc = branchsrc.strip()
            path = branchtarget(branchnum)
            branchdest = os.path.join(destination, path)
            branches.append(branchfactory.produce(branchsrc, branchdest))
        return branches

    def lock(self):
        self.actualLock = lockfile.LockFile(config.masterlock)
        try:
            self.actualLock.acquire()
        except OSError, e:
            raise LockError

    def unlock(self):
        self.actualLock.release()


class JobManagerError(StandardError):
    def __str__(self):
        return 'Unknown Jobmanager error: %s' \
                % (self.__class__.__name__, str(e))


class LockError(JobManagerError):
    def __str__(self):
        return 'Jobmanager unable to get master lock'

class JobManagerController:
    """A class to control a Job Manager."""

    killSignal = signal.SIGTERM

    def kill(self):
        """Sends kills to JobManager"""
        os.kill(os.getpid(), self.killSignal)

