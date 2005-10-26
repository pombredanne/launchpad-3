import psycopg
import sys
import logging
import os.path
import string
from datetime import datetime
import pickle

from twisted.internet import reactor
from twisted.spread import pb
from twisted.python import log

from buildbot.process.base import BasicBuildFactory
from buildbot.process.step import ShellCommand,BuildStep
from buildbot.process.base import ConfigurableBuildFactory, ConfigurableBuild
from buildbot.status.progress import Expectations
from buildbot.status.event import Event

from importd.Job import CopyJob

from canonical.lp import initZopeless
from canonical.launchpad.database import Product, ProductSeries
from canonical.database.constants import UTC_NOW

from canonical.lp.dbschema import ImportStatus


def _interval_to_seconds(interval):
    try:
        return interval.days * 24 * 60 * 60 + interval.seconds
    except AttributeError:
        msg = "Failed to convert interval to seconds: %r" % (interval,)
        raise TypeError(msg)

class LogAdaptor(logging.Handler):
    """I present a logging.Logger interface and log the results
    to a callable"""
    def __init__(self, sink):
        self.sink=sink
        logging.Handler.__init__(self)
    def emit(self, record):
        """Log record to the sink"""
        self.sink("%s\n" % record.getMessage())

class LoggingLogAdaptor(logging.Handler):
    """I present a logging.Logger interface and log the results to a
    twisted log.msg interface"""
    def __init__(self, log):
        self.logger=log
        logging.Handler.__init__(self)
    def emit(self, record):
        """Log record to the log.msg interface"""
        self.logger.msg(record.getMessage())


### Former jobstuff.py. Beware, here be cruft! ###

# job import logic
def getTxnManager():
    """get a current ZopelessTransactionManager"""
    # FIXME: That uses a protected attribute in ZopelessTransactionManager
    # -- David Allouche 2005-02-16
    from canonical.database.sqlbase import ZopelessTransactionManager
    if ZopelessTransactionManager._installed is None:
        return initZopeless(implicitBegin=False)
    else:
        return ZopelessTransactionManager._installed

def tryToAbortTransaction():
    """Try to abort the transaction, ignore psycopg.Error.

    If some of our database-talking code raises, we want to be sure we have
    aborted any transaction we may have started, otherwise a subsequent begin()
    would fail. Broadly, the error conditions are of two sorts:

      * something went wrong in our code, we could handle that case more
        cleanly by aborting the transaction only if we have started one.

      * something went wrong with the database (like a lost connection), in
        that case, abort will likely fail.

    So, anyway, we need a way to abort() that works even if abort() would fail.

    :note: this function should only be used in exception handlers to provide
        graceful recovery. It is _not_ a proper way to abort a transaction.
    """
    try:
        getTxnManager().abort()
    except psycopg.Error:
        pass


def jobsFromDB(slave_home, archive_mirror_dir, autotest):
    if autotest:
        importstatus = [ImportStatus.TESTING,
                        ImportStatus.TESTFAILED,
                        ImportStatus.AUTOTESTED]
    else:
        importstatus = [ImportStatus.PROCESSING,
                        ImportStatus.SYNCING]
    try:
        clause = ('importstatus in (%s)' %
                  ', '.join([str(status.value) for status in importstatus]))
        getTxnManager().begin()
        jobseries = ProductSeries.select(clause)
        jobs = list(jobsFromSeries(jobseries, slave_home, archive_mirror_dir))
        getTxnManager().abort()
    except:
        tryToAbortTransaction()
        raise
    return jobs

def jobsFromSeries(jobseries, slave_home, archive_mirror_dir):
    for series in jobseries:
        job = CopyJob()
        job.from_series(series)
        job.slave_home = slave_home
        job.archive_mirror_dir = archive_mirror_dir
        yield job

def jobsBuilders(jobs, slavenames, runner_path=None, autotest=False):
    builders = []
    for job in jobs:
        factory = ImportDShellBuildFactory(job, job.slave_home,
                                           runner_path, autotest)
        builders.append({
            'name': job.name, 
            'slavename': slavenames[hash(job.name) % len(slavenames)],
            'builddir': "buildbot-jobs", 'factory': factory,
            'periodicBuildTime': job.frequency})
    return builders

def productJobsDict(jobs):
    """Mapping of products to jobs.

    :type jobs: iterable of importd.Job.Job
    :return: mapping from product ids to jobs.
    :rtype: dict of int to buildbot.importd.Job.Job
    """
    by_product = {}
    for job in jobs:
        product_jobs = by_product.get(job.product_id, [])
        product_jobs.append(job)
        by_product[job.product_id] = product_jobs
    return by_product

def anonymousInterlock(jobs):
    """Create anonymous interlock between for sources and packages.

    :type jobs: iterable of importd.Job.Job
    :return: anonymous interlock ([sources], [packages]), or ``None`` if there
        are no sources or no packages.
    :rtype: 2-tuple of lists of importd.Job.Job or ``None``
    """
    sources, packages = [], []
    for job in jobs:
        if job.RCS == 'package':
            packages.append(job.name)
        elif job.RCS in ('cvs', 'svn'):
            sources.append(job.name)
        else:
            raise RuntimeError('RCS of job %r is %r'
                               % (job.name, job.RCS))
    if len(sources) == 0 or len(packages) == 0:
        return None
    else:
        return sources, packages

def nameInterlock(product_id, interlock):
    """Put the product name into an anonymous interlock.

    :param product_id: id of the product associated to the interlock
    :param interlock: ([feeders], [watchers]) pair
    :precondition: all jobs in the interlock have product_id.
    :return: named interlock, ("name", [feeders], [watchers])
    """
    feeders, watchers = interlock
    name = Product.get(product_id).name
    return name, feeders, watchers

def jobsInterlocks(jobs):
    """Create interlocks for the given jobs.

    :param jobs: jobs to create interlocks for.
    :type jobs: iterable of importd.Job.Job
    :return: interlocks for BuildmasterConfig.
    :rtype: list of (name, [feeders], [watchers]) tuples
    """
    interlocks = []
    by_product = productJobsDict(jobs)
    for product_id, product_jobs in by_product.items():
        anon = anonymousInterlock(product_jobs)
        if anon is not None:
            inter = nameInterlock(product_id, anon)
            interlocks.append(inter)
    return interlocks


from twisted.python.failure import Failure

class NotifyingBuild(ConfigurableBuild):
    """Build that notifies of starts and finishes and can refresh itself.
    """

    def getObserver(self):
        raise NotImplementedError

    def startBuild(self, remote, progress):
        self.__finished = False
        try:
            self.getObserver().startBuild()
        except:
            f = Failure()
            tryToAbortTransaction()
            return self.buildException(f, "startBuild")
        return ConfigurableBuild.startBuild(self, remote, progress)

    def buildFinished(self, event, successful=1):
        if not self.__finished:
            # catch recursive calls caused by a failure in observer
            self.__finished = True
            try:
                self.getObserver().buildFinished(successful)
            except:
                f = Failure()
                tryToAbortTransaction()
                # that will cause buildFinished to be called recursively
                self.buildException(f, "buildFinished")
        ConfigurableBuild.buildFinished(self, event, successful)

    def refreshBuilder(self, rerun, periodic):
        self.builder.stopPeriodicBuildTimer()
        # change the builder and run it again after the buildFinished 
        # process finishes.
        # XXX: This should not be needed. It is needed because we are
        # in a deep call stack which will call into
        # self.build.builder.expectations which is currently coupled
        # to the value of self.build.builder.steps.
        # If this is fixed, we can simply call self.refreshBuilder().
        reactor.callLater(1, self.refreshBuilderDelayed, rerun, periodic)

    def refreshBuilderDelayed(self, rerun, periodic):
        """refresh the builder and then force a build"""
        # This might be better as a helper function in the module, but that
        # feels more unclean than duplicating these lines as they come from
        # several not-well-connected places
        self.builder.buildFactory.steps = []
        self.builder.buildFactory.addSteps()
        self.builder.waiting = self.builder.newBuild()
        self.builder.expectations = None
        p = self.builder.waiting.setupProgress()
        if p:
            self.builder.expectations = Expectations(p)
        self.builder.periodicBuildTime = periodic
        self.builder.startPeriodicBuildTimer()
        if rerun:
            self.builder.forceBuild("botmaster", "import completed",
                                    periodic=False)


class ImportDBuild(NotifyingBuild):
    """Build that updates the database with RCS import status."""

    def getObserver(self):
        return ImportDBImplementor(self)


class ImportDBImplementor(object):
    """Implementation of the ImportDBuild behaviour, separates namespaces.

    This implementor should be instantiated in every method overriden by
    ImportDBuild. It allows easy extension of ImportDBuild without running the
    risk of namespace clashes with buildbot.
    """

    def __init__(self, build):
        assert build.importDJob is not None
        # make sure this is an upstream code import, not a package import
        assert build.importDJob.RCS in ['cvs', 'svn']
        self.seriesID = build.importDJob.seriesID
        self.build = build

    def getSeries(self):
        """return the sourcesource our job is for"""
        return ProductSeries.get(self.seriesID)

    def startBuild(self):
        getTxnManager().begin()
        self.setDateStarted()
        getTxnManager().commit()

    def setDateStarted(self):
        self.getSeries().datestarted = UTC_NOW

    def buildFinished(self, successful):
        getTxnManager().begin()
        self.setDateFinished()
        if self.getSeries().importstatus in [ImportStatus.TESTING,
                                             ImportStatus.AUTOTESTED,
                                             ImportStatus.TESTFAILED]:
            self.setAutotested(successful)
        elif self.getSeries().importstatus == ImportStatus.PROCESSING:
            self.processingComplete(successful)
        getTxnManager().commit()

    def setDateFinished(self):
        self.getSeries().datefinished = UTC_NOW

    def setAutotested(self, successful):
        """Autotest run is complete, update database and buildbot.

        Update importstatus according to success or failure, and do not rerun
        the job.
        """
        series = self.getSeries()
        self.build.importDJob.frequency = 0
        if successful:
            series.dateautotested = UTC_NOW
            series.importstatus = ImportStatus.AUTOTESTED
        else:
            series.importstatus = ImportStatus.TESTFAILED
        self.refreshBuilder(rerun=False)

    def processingComplete(self, successful):
        """Impot or sync run is complete, update database and buildbot.

        If the job was an import, make it a sync and rerun it immediately.
        """
        series = self.getSeries()
        if series.importstatus == ImportStatus.PROCESSING and successful:
            series.enableAutoSync()
            self.build.importDJob.TYPE = 'sync'
            self.build.importDJob.frequency = _interval_to_seconds(
                self.getSeries().syncinterval)
            self.refreshBuilder(rerun = True)

    def refreshBuilder(self, rerun):
        periodic = self.build.importDJob.frequency
        self.build.refreshBuilder(rerun=rerun, periodic=periodic)


class ImportDBuildFactory(ConfigurableBuildFactory):

    buildClass = ImportDBuild

    def __init__(self, job, jobfile, autotest=False):
        self.steps = []
        self.job = job
        self.jobfile = jobfile
        self.autotest = autotest
        self.addSteps()

    def addSteps(self):
        if self.job.TYPE == "import":
            self.addImportDStep('nukeTargets')
            self.addImportDStep('runJob')
        elif self.job.TYPE == 'sync':
            self.addImportDStep('runJob')
            if not self.autotest:
                self.addImportDStep('mirrorTarget')

    def addImportDStep(self, method):
        steps.append((RunJobStep, {
            'job': self.job,
            'method': 'mirrorTarget',
            'workdir': self.jobfile}))

    def newBuild(self):
        # Save the job inside the build, so the startBuild and buildFinished
        # handlers can use it
        result = ConfigurableBuildFactory.newBuild(self)
        result.importDJob = self.job
        return result


class ImportDShellBuildFactory(ImportDBuildFactory):

    def __init__(self, job, jobfile, runner_path, autotest):
        if runner_path is None:
            self.runner_path = os.path.join(os.path.dirname(__file__),
                                            'CommandLineRunner.py')
        else:
            self.runner_path = str(runner_path)
        ImportDBuildFactory.__init__(self, job, jobfile, autotest)

    def addSteps(self):
        self.addMakeJobFileStep()
        ImportDBuildFactory.addSteps(self)

    def addMakeJobFileStep(self):
        self.steps.append((MakeJobFileStep, {
            'job': self.job,
            'jobfile': self.job.name,
            'workdir': self.jobfile}))

    def addImportDStep(self, method):
        self.steps.append((ImportDShellCommand, {
            'timeout': 1200,
            'workdir': self.jobfile,
            'command': [sys.executable, self.runner_path,
                        self.job.name, method, '.'],}))


class ImportDShellCommand(ShellCommand):

    # Failure on a step prevents running any subsequent step. For example, if
    # upstream CVS moves files by altering the repository, we do not want to
    # mirror any revision before applying a fix by hand.
    haltOnFailure = 1

    def words(self):
        return [self.command[3]]


from buildbot.status.event import Logfile
from buildbot.process.step import FAILURE,WARNINGS,SUCCESS,SKIPPED

class JobBuildStep(BuildStep):
    """ I serialise a job to a jobfile"""

    flunkOnFailure = True
    progressMetrics = ['output']

    def __init__(self, **kwargs):
        BuildStep.__init__(self, **kwargs)

    def startStatus(self):
        label = ["running"] + self.words()
        event = Event("yellow", label, files={'log': self.log})
        self.setCurrentActivity(event)

    def addStdout(self, data):
        self.log.addStdout(data)

    def addStderr(self, data):
        self.log.addStderr(data)

    def addHeader(self, data):
        self.log.addHeader(data)

    def remoteUpdate(self, update):
        if update.has_key('stdout'):
            self.addStdout(update['stdout'])
        if update.has_key('stderr'):
            self.addStderr(update['stderr'])
        if update.has_key('header'):
            self.addHeader(update['header'])
        if update.has_key('rc'):
            rc = self.rc = update['rc']
            self.addHeader("program finished with exit code %d\n" % rc)
    #def remoteUpdate(self,update):
    #    if update.has_key('header'):
    #       self.addHeader(update['header'])

    def addHeader(self, header):
        self.log.addHeader(header)

    def remoteComplete(self, failure=None):
        log.msg("remote complete", self.stepId)
        self.log.finish()
        if failure:
            log.msg("remote command failed!")
            return self.stepFailed(failure)
        else:
            return self.finished()

    def finished(self):
        log.msg("JobBuildStep finished")
        # can do other processing here
        output = self.log.getAll()
        return self.stepComplete(SUCCESS)
        #(SUCCESS, output))

    def finishStatus(self, result):
        log.msg("JobBuildStep.finishStatus:", result)
        # by default, red if rc != 0
        import types
        if type(result) == types.TupleType:
            result, text_ignored = result
        if result == FAILURE:
            self.updateCurrentActivity(color= "red",
                                       text= self.words() + ["failed"])
        elif result == WARNINGS:
            self.updateCurrentActivity(color= "orange",
                                       text= self.words() + ["warnings"])
        else:
            self.updateCurrentActivity(color= "green",
                                       text= self.words() + ["successful"])
        self.finishCurrentActivity()


class MakeJobFileStep(JobBuildStep):
    """ I serialise a job to a jobfile"""

    def __init__(self, job, jobfile, workdir=".", **kwargs):
        JobBuildStep.__init__(self, **kwargs)
        self.job = job
        self.jobfile = jobfile
        self.workdir=workdir
        self.log = Logfile()

    def words(self):
        return ["makeJobFile"]

    def start(self):
        assert(self.job != None)
        what = "job file %s" % (self.jobfile)
        log.msg(what)
        args = {'job': self.job,
                'method': 'toFile',
                'args': [os.path.join(self.workdir, self.jobfile)],
                'dir': self.workdir
        }
        #here, these are all passed to the child's copy of <class>. There is
        # a case based constructor on the child, which is used to determine
        # the class to instantiate.
        #
        #args = {'command': self.command,
        #        'dir': self.workdir,
        #        'env': self.env,
        #        # env, want_stdout, want_stderr
        #        'timeout': self.timeout
        #        }
        d = self.remote.callRemote("startCommand", self, self.stepId,
                                  "job", args)
        # might raise UnknownCommand if it isn't implemented
        d.addErrback(self.stepFailed)


class RunJobStep(JobBuildStep):
    """ I 'run' a job as a single operation"""

    def __init__(self, job, method,workdir=".", **kwargs):
        JobBuildStep.__init__(self, **kwargs)
        self.job = job
        self.workdir=workdir
        self.log = Logfile()
        self.method=method
        self.name="%s" % self.words()

    def words(self):
        return ["runJobStep %s" % self.method]

    def start(self):
        assert(self.job != None)
        args = {'job': self.job,
                'method': self.method,
                'args': [],
                'dir': self.workdir
        }
        #here, these are all passed to the child's copy of <class>. There is
        # a case based constructor on the child, which is used to determine
        # the class to instantiate.
        #
        #args = {'command': self.command,
        #        'dir': self.workdir,
        #        'env': self.env,
        #        # env, want_stdout, want_stderr
        #        'timeout': self.timeout
        #        }
        d = self.remote.callRemote("startCommand", self, self.stepId,
                                  "job", args)
        # might raise UnknownCommand if it isn't implemented
        d.addErrback(self.stepFailed)

