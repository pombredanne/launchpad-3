import psycopg
import sys
import logging
import os.path

from twisted.internet import reactor
from twisted.python import log
from twisted.python.failure import Failure

from buildbot.process.step import ShellCommand, BuildStep
from buildbot.process.base import ConfigurableBuildFactory, ConfigurableBuild
from buildbot.status.progress import Expectations
from buildbot.status.event import Event

from importd.Job import CopyJob

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.launchpad.database import ProductSeries
from canonical.launchpad.interfaces import ImportStatus
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.webapp import canonical_url, errorlog
from canonical.lp import initZopeless


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
        self.sink = sink
        logging.Handler.__init__(self)
    def emit(self, record):
        """Log record to the sink"""
        self.sink("%s\n" % record.getMessage())

class LoggingLogAdaptor(logging.Handler):
    """I present a logging.Logger interface and log the results to a
    twisted log.msg interface"""
    def __init__(self, log):
        self.logger = log
        logging.Handler.__init__(self)
    def emit(self, record):
        """Log record to the log.msg interface"""
        self.logger.msg(record.getMessage())


def getTxnManager():
    """Get a current ZopelessTransactionManager, execute zcml if needed.

    We do not have a convenient hook to run initZopeless and
    execute_zcml_for_scripts at botmaster start-up. This function should be
    used when database access in needed, it return a transaction manager that
    can be used to open a transaction. It will call initZopeless and
    execute_zcml_for_scripts if necessary.
    """
    # FIXME: That uses a protected attribute in ZopelessTransactionManager
    # -- David Allouche 2005-02-16
    from canonical.database.sqlbase import ZopelessTransactionManager
    if ZopelessTransactionManager._installed is None:
        execute_zcml_for_scripts()
        return initZopeless(implicitBegin=False)
    else:
        return ZopelessTransactionManager._installed


def tryToAbortTransaction():
    """Try to abort the transaction, ignore psycopg.Error.

    If some of our database-talking code raises, we want to be sure we have
    aborted any transaction we may have started, otherwise a subsequent
    begin() would fail. Broadly, the error conditions are of two sorts:

      * something went wrong in our code, we could handle that case more
        cleanly by aborting the transaction only if we have started one.

      * something went wrong with the database (like a lost connection), in
        that case, abort will likely fail.

    So, anyway, we need a way to abort() that works even if abort() would
    fail.

    :note: this function should only be used in exception handlers to provide
        graceful recovery. It is _not_ a proper way to abort a transaction.
    """
    try:
        getTxnManager().abort()
    except psycopg.Error:
        pass


def buildersFromDatabase(config):
    """Return a list of Builder instances from ProductSeries in the database.

    This is called by from botmaster/master.cfg. That file is executed by
    Buildbot on initialization and when reloading the builders.

    :param config: botmaster configuration module.
    :return: list of buildbot Builder instances for active bazaar imports.
    """
    try:
        jobs = jobsFromDB(
            slave_home = config.slavehome,
            archive_mirror_dir = config.baz_mirrors,
            autotest = config.autotest,
            push_prefix=config.bzr_mirrors)
        slaves = config.private.bot_passwords.keys()
        builders = jobsBuilders(
            jobs, slaves,
            importd_path=config.importd_path,
            push_prefix=config.bzr_mirrors,
            source_repo=config.source_repository,
            blacklist_path=config.blacklist_path,
            autotest = config.autotest)
        return builders
    except:
        # Bare except, log OOPSes for all exceptions. Although we should only
        # get database-related exceptions from here.
        reportOops(config.autotest)
        raise


def jobsFromDB(slave_home, archive_mirror_dir, autotest, push_prefix):
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
        jobs = list(jobsFromSeries(
            jobseries=jobseries,
            slave_home=slave_home,
            archive_mirror_dir=archive_mirror_dir,
            push_prefix=push_prefix,
            autotest=autotest))
        getTxnManager().abort()
    except:
        tryToAbortTransaction()
        raise
    return jobs

def jobsFromSeries(jobseries, slave_home, archive_mirror_dir, push_prefix,
                   autotest):
    for series in jobseries:
        job = CopyJob()
        job.from_series(series)
        job.slave_home = slave_home
        job.archive_mirror_dir = archive_mirror_dir
        job.push_prefix = push_prefix
        job.autotest = autotest
        # Record the canonical url of the series now, althought it is only
        # needed for oops reporting, so we can record BuildFailure OOPSes even
        # without database access. To use canonical_url we need to have run
        # execute_zcml_for_scripts, which is done in getTxnManager.
        job.series_url = canonical_url(series)
        yield job

def jobsBuilders(jobs, slavenames, importd_path, push_prefix,
                 source_repo, blacklist_path='/dev/null',
                 autotest=False):
    builders = []
    for job in jobs:
        factory = ImportDShellBuildFactory(
            job, job.slave_home, importd_path, push_prefix,
            blacklist_path, source_repo, autotest)
        builders.append({
            'name': job.name, 
            'slavename': slavenames[hash(job.name) % len(slavenames)],
            'builddir': "buildbot-jobs", 'factory': factory,
            'periodicBuildTime': job.frequency})
    return builders


class BuildFailure(Exception):
    """Exception recorded in OOPS for failed importd jobs."""


def reportOops(autotest, info=None, request=None):
    """Record an OOPS and log the OOPS id.

    Since we do not have a good hooking place to configure the OOPS reporting
    system on botmaster startup, we do the configuration whenever we need to
    report an OOPS. It is a bit ugly, but it should not be a problem.
    """
    if info is None:
        info = sys.exc_info()
    if request is None:
        request = errorlog.ScriptRequest([])
    # Instanciating ErrorReportingUtility every time is not thread safe,
    # but it's not important because botmaster is single-threaded. And it
    # ensure that the modified configuration is used.
    error_reporting_utility = errorlog.ErrorReportingUtility()
    if autotest:
        error_reporting_utility.configure('importd_autotest')
    else:
        error_reporting_utility.configure('importd')
    error_reporting_utility.raising(info, request)
    log.msg(" Recorded", request.oopsid)


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
            # Catch any exception, log an OOPS, safely abort the transaction,
            # convert the exception into a Twisted failure and pass it.
            # Leaving the exception bubble up breaks Buildbot.
            self.importdReportException()
            f = Failure()
            tryToAbortTransaction()
            return self.buildException(f, "startBuild")
        return ConfigurableBuild.startBuild(self, remote, progress)

    def buildFinished(self, event, successful=1):
        if not self.__finished:
            # catch recursive calls caused by a failure in observer
            self.__finished = True
            try:
                if not successful:
                    # Log a build failure OOPS before trying to update the
                    # database, because the database access may raise an
                    # exception, that will be logged separately.
                    self.importdReportBuildFailure()
                self.getObserver().buildFinished(successful)
            except:
                # Catch any exception, log an OOPS, safely abort the
                # transaction, convert the exception into a Twisted failure
                # and pass it. Letting the exception rise breaks Buildbot.
                self.importdReportException()
                f = Failure()
                tryToAbortTransaction()
                # that will cause buildFinished to be called recursively
                self.buildException(f, "buildFinished")
        ConfigurableBuild.buildFinished(self, event, successful)

    def refreshBuilder(self, rerun, periodic):
        self.builder.stopPeriodicBuildTimer()
        # Change the builder and run it again after the buildFinished process
        # finishes. callLater not be needed. It is needed because we are in a
        # deep call stack which will call into self.build.builder.expectations
        # which is currently coupled to the value of self.build.builder.steps.
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
        progress = self.builder.waiting.setupProgress()
        if progress:
            self.builder.expectations = Expectations(progress)
        self.builder.periodicBuildTime = periodic
        self.builder.startPeriodicBuildTimer()
        if rerun:
            self.builder.forceBuild("botmaster", "import completed",
                                    periodic=False)

    def importdReportException(self):
        """Record an OOPS for the current exception.

        Usually, exceptions are caused by database connection problems. So we
        just log an OOPS for the exception and we do not try to give
        additional details.
        """
        reportOops(self.importd_autotest)

    def importdReportBuildFailure(self):
        """Record an OOPS for the current failed job."""
        # This method should not use the database, so we can accurately record
        # build failures even without database access.
        request = errorlog.ScriptRequest([
            ('series.id', self.importDJob.seriesID)],
            # XXX: DavidAllouche 2007-04-05:
            # It would be nice to show step.words() and the step log here
            # when recording a build failure. But I do not know how to
            # retrieve this data. I tried looking at the buildbot code, but
            # then the magic smoke started to escape out of my ears.
            URL=self.importDJob.series_url)
        # XXX: DavidAllouche 2007-04-05:
        # We should be using step.words() as the BuildFailure argument to
        # produce good oops summaries, but we do not have this data.
        reportOops(self.importd_autotest,
            (BuildFailure, BuildFailure(), None), request)


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
        importstatus = self.getSeries().importstatus
        if importstatus in [ImportStatus.TESTING,
                            ImportStatus.AUTOTESTED,
                            ImportStatus.TESTFAILED]:
            self.setAutotested(successful)
        if importstatus == ImportStatus.PROCESSING:
            self.processingComplete(successful)
        if successful and importstatus in [ImportStatus.PROCESSING,
                                           ImportStatus.SYNCING]:
            self.getSeries().importUpdated()
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
        """Import run is complete, update database and buildbot.

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

    def __init__(self, job, jobfile, autotest):
        self.steps = []
        self.job = job
        self.jobfile = jobfile
        self.autotest = autotest
        self.addSteps()

    def addSteps(self):
        if self.job.TYPE == "import":
            self.addImportDStep('nukeTargets')
            self.addImportDStep('runJob')
            if not self.autotest:
                self.addSourceTransportStep('importd-put-source.py')
                self.addImportDStep('mirrorTarget')
        elif self.job.TYPE == 'sync':
            if not self.autotest:
                self.addSourceTransportStep('importd-get-source.py')
            self.addImportDStep('runJob')
            if not self.autotest:
                self.addSourceTransportStep('importd-put-source.py')
                self.addImportDStep('mirrorTarget')

    def addImportDStep(self, method):
        raise NotImplementedError

    def newBuild(self):
        # Save the job and the autotest flag inside the build, so the
        # startBuild and buildFinished handlers can use them.
        result = ConfigurableBuildFactory.newBuild(self)
        result.importDJob = self.job
        result.importd_autotest = self.autotest
        return result


class ImportDShellBuildFactory(ImportDBuildFactory):

    def __init__(self, job, jobfile, importd_path, push_prefix,
                 blacklist_path, source_repo, autotest):
        if importd_path is None:
            importd_path = os.path.dirname(__file__)
        self.runner_path = os.path.join(importd_path, 'CommandLineRunner.py')
        self.baz2bzr_path = os.path.join(importd_path, 'baz2bzr.py')
        self.push_prefix = push_prefix
        self.blacklist_path = blacklist_path
        self.source_repo = source_repo
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
            'timeout': 14400,
            'workdir': self.jobfile,
            'command': [sys.executable, self.runner_path,
                        self.job.name, method, '.'],}))

    def addBaz2bzrStep(self):
        workdir = self.job.getWorkingDir(self.jobfile)
        self.steps.append((Baz2bzrShellCommand, {
            'timeout': 14400,
            'workdir': workdir,
            'command': [sys.executable, self.baz2bzr_path,
                        str(self.job.seriesID), self.blacklist_path,
                        self.push_prefix],}))

    def addSourceTransportStep(self, script):
        workdir = self.job.getWorkingDir(self.jobfile, create=False)
        script_path = os.path.join(config.root, 'scripts', script)
        source_name = {'cvs': 'cvsworking',
                       'svn': 'svnworking'}[self.job.RCS.lower()]
        local_source = os.path.join(workdir, source_name)
        remote_dir = (
            self.source_repo.rstrip('/') + '/%08x' % self.job.seriesID)
        self.steps.append((SourceTransportShellCommand, {
            'workdir': workdir,
            'command': [sys.executable, script_path,
                        local_source, remote_dir],}))


class ImportDShellCommand(ShellCommand):

    # Failure on a step prevents running any subsequent step. For example, if
    # upstream CVS moves files by altering the repository, we do not want to
    # mirror any revision before applying a fix by hand.
    haltOnFailure = 1

    def words(self):
        return [self.command[3]]


class Baz2bzrShellCommand(ShellCommand):

    # Failure on a step prevents running any subsequent step. For example, if
    # upstream CVS moves files by altering the repository, we do not want to
    # mirror any revision before applying a fix by hand.
    haltOnFailure = 1

    def words(self):
        return ['baz2bzr', self.command[3]]


class SourceTransportShellCommand(ShellCommand):

    # Failure on a step prevents running any subsequent step. For example, if
    # upstream CVS moves files by altering the repository, we do not want to
    # mirror any revision before applying a fix by hand.
    haltOnFailure = 1

    def words(self):
        command = os.path.basename(self.command[1])
        return [{'importd-get-source.py': 'get-source',
                 'importd-put-source.py': 'put-source'}.get(command, command)]


from buildbot.status.event import Logfile
from buildbot.process.step import FAILURE, WARNINGS, SUCCESS

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
        self.workdir = workdir
        self.log = Logfile()

    def words(self):
        return ["makeJobFile"]

    def start(self):
        assert(self.job != None)
        what = "job file %s" % (self.jobfile)
        log.msg(what)
        args = {'job': self.job,
                'method': 'prepare',
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
