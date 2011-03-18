# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Facilities for running Jobs."""


__metaclass__ = type


__all__ = [
    'BaseRunnableJob',
    'JobCronScript',
    'JobRunner',
    'JobRunnerProcess',
    'TwistedJobRunner',
    ]


from calendar import timegm
from collections import defaultdict
import contextlib
import logging
import os
from signal import (
    getsignal,
    SIGCHLD,
    SIGHUP,
    signal,
    )
import sys

from ampoule import (
    child,
    main,
    pool,
    )
from lazr.delegates import delegates
import transaction
from twisted.internet import (
    defer,
    reactor,
    )
from twisted.protocols import amp
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad import scripts
from canonical.launchpad.webapp import errorlog
from canonical.lp import initZopeless
from lp.services.job.interfaces.job import (
    IJob,
    IRunnableJob,
    LeaseHeld,
    )
from lp.services.mail.sendmail import MailController
from lp.services.scripts.base import LaunchpadCronScript
from lp.services.twistedsupport.task import (
    ParallelLimitedTaskConsumer,
    PollingTaskSource,
    )


class BaseRunnableJob:
    """Base class for jobs to be run via JobRunner.

    Derived classes should implement IRunnableJob, which requires implementing
    IRunnableJob.run.  They should have a `job` member which implements IJob.

    Subclasses may provide getOopsRecipients, to send mail about oopses.
    If so, they should also provide getOperationDescription.
    """
    delegates(IJob, 'job')

    user_error_types = ()

    # We redefine __eq__ and __ne__ here to prevent the security proxy
    # from mucking up our comparisons in tests and elsewhere.
    def __eq__(self, job):
        return (
            self.__class__ is removeSecurityProxy(job.__class__)
            and self.job == job.job)

    def __ne__(self, job):
        return not (self == job)

    def getOopsRecipients(self):
        """Return a list of email-ids to notify about oopses."""
        return self.getErrorRecipients()

    def getOperationDescription(self):
        return 'unspecified operation'

    def getErrorRecipients(self):
        """Return a list of email-ids to notify about user errors."""
        return []

    def getOopsMailController(self, oops_id):
        """Return a MailController for notifying people about oopses.

        Return None if there is no-one to notify.
        """
        recipients = self.getOopsRecipients()
        if len(recipients) == 0:
            return None
        subject = 'Launchpad internal error'
        body = (
            'Launchpad encountered an internal error during the following'
            ' operation: %s.  It was logged with id %s.  Sorry for the'
            ' inconvenience.' % (self.getOperationDescription(), oops_id))
        from_addr = config.canonical.noreply_from_address
        return MailController(from_addr, recipients, subject, body)

    def getUserErrorMailController(self, e):
        """Return a MailController for notifying about user errors.

        Return None if there is no-one to notify.
        """
        recipients = self.getErrorRecipients()
        if len(recipients) == 0:
            return None
        subject = 'Launchpad error while %s' % self.getOperationDescription()
        body = (
            'Launchpad encountered an error during the following'
            ' operation: %s.  %s' % (self.getOperationDescription(), str(e)))
        from_addr = config.canonical.noreply_from_address
        return MailController(from_addr, recipients, subject, body)

    def notifyOops(self, oops):
        """Report this oops."""
        ctrl = self.getOopsMailController(oops.id)
        if ctrl is None:
            return
        ctrl.send()

    def getOopsVars(self):
        """See `IRunnableJob`."""
        return [('job_id', self.job.id)]

    def notifyUserError(self, e):
        """See `IRunnableJob`."""
        ctrl = self.getUserErrorMailController(e)
        if ctrl is None:
            return
        ctrl.send()

    @staticmethod
    @contextlib.contextmanager
    def contextManager():
        yield


class BaseJobRunner(object):
    """Runner of Jobs."""

    def __init__(self, logger=None, error_utility=None):
        self.completed_jobs = []
        self.incomplete_jobs = []
        if logger is None:
            logger = logging.getLogger()
        self.logger = logger
        self.error_utility = error_utility
        if self.error_utility is None:
            self.error_utility = errorlog.globalErrorUtility

    def runJob(self, job):
        """Attempt to run a job, updating its status as appropriate."""
        job = IRunnableJob(job)

        self.logger.debug(
            'Running job in status %s' % (job.status.title,))
        job.start()
        transaction.commit()

        try:
            job.run()
        except Exception:
            self.logger.exception("Job execution raised an exception.")
            transaction.abort()
            job.fail()
            # Record the failure.
            transaction.commit()
            self.incomplete_jobs.append(job)
            raise
        else:
            # Commit transaction to update the DB time.
            transaction.commit()
            job.complete()
            self.completed_jobs.append(job)
        # Commit transaction to update job status.
        transaction.commit()

    def runJobHandleError(self, job):
        """Run the specified job, handling errors.

        Most errors will be logged as Oopses.  Jobs in user_error_types won't.
        The list of complete or incomplete jobs will be updated.
        """
        job = IRunnableJob(job)
        with self.error_utility.oopsMessage(
            dict(job.getOopsVars())):
            try:
                try:
                    self.logger.debug('Running %r', job)
                    self.runJob(job)
                except job.user_error_types, e:
                    job.notifyUserError(e)
                except Exception:
                    info = sys.exc_info()
                    return self._doOops(job, info)
            except Exception:
                # This only happens if sending attempting to notify users
                # about errors fails for some reason (like a misconfigured
                # email server).
                self.logger.exception(
                    "Failed to notify users about a failure.")
                info = sys.exc_info()
                # Returning the oops says something went wrong.
                return self.error_utility.raising(info)

    def _doOops(self, job, info):
        """Report an OOPS for the provided job and info.

        :param job: The IRunnableJob whose run failed.
        :param info: The standard sys.exc_info() value.
        :return: the Oops that was reported.
        """
        oops = self.error_utility.raising(info)
        job.notifyOops(oops)
        return oops

    def _logOopsId(self, oops_id):
        """Report oopses by id to the log."""
        if self.logger is not None:
            self.logger.info('Job resulted in OOPS: %s' % oops_id)


class JobRunner(BaseJobRunner):

    def __init__(self, jobs, logger=None):
        BaseJobRunner.__init__(self, logger=logger)
        self.jobs = jobs

    @classmethod
    def fromReady(cls, job_class, logger=None):
        """Return a job runner for all ready jobs of a given class."""
        return cls(job_class.iterReady(), logger)

    @classmethod
    def runFromSource(cls, job_source, dbuser, logger):
        """Run all ready jobs provided by the specified source.

        The dbuser parameter is ignored.
        """
        with removeSecurityProxy(job_source.contextManager()):
            logger.info("Running synchronously.")
            runner = cls.fromReady(job_source, logger)
            runner.runAll()
        return runner

    def runAll(self):
        """Run all the Jobs for this JobRunner."""
        for job in self.jobs:
            job = IRunnableJob(job)
            self.logger.debug(
                'Trying to acquire lease for job in state %s' % (
                    job.status.title,))
            try:
                job.acquireLease()
            except LeaseHeld:
                self.logger.debug('Could not acquire lease for job')
                self.incomplete_jobs.append(job)
                continue
            # Commit transaction to clear the row lock.
            transaction.commit()
            oops = self.runJobHandleError(job)
            if oops is not None:
                self._logOopsId(oops.id)


class RunJobCommand(amp.Command):

    arguments = [('job_id', amp.Integer())]
    response = [('success', amp.Integer()), ('oops_id', amp.String())]


def import_source(job_source_name):
    """Return the IJobSource specified by its full name."""
    module, name = job_source_name.rsplit('.', 1)
    source_module = __import__(module, fromlist=[name])
    return getattr(source_module, name)


class JobRunnerProcess(child.AMPChild):
    """Base class for processes that run jobs."""

    def __init__(self, job_source_name, dbuser):
        child.AMPChild.__init__(self)
        self.job_source = import_source(job_source_name)
        self.context_manager = self.job_source.contextManager()
        # icky, but it's really a global value anyhow.
        self.__class__.dbuser = dbuser

    @classmethod
    def __enter__(cls):

        def handler(signum, frame):
            raise TimeoutError
        scripts.execute_zcml_for_scripts(use_web_security=False)
        signal(SIGHUP, handler)
        initZopeless(dbuser=cls.dbuser)

    @staticmethod
    def __exit__(exc_type, exc_val, exc_tb):
        pass

    def makeConnection(self, transport):
        """The Job context is entered on connect."""
        child.AMPChild.makeConnection(self, transport)
        self.context_manager.__enter__()

    def connectionLost(self, reason):
        """The Job context is left on disconnect."""
        self.context_manager.__exit__(None, None, None)
        child.AMPChild.connectionLost(self, reason)

    @RunJobCommand.responder
    def runJobCommand(self, job_id):
        """Run a job from this job_source according to its job id."""
        runner = BaseJobRunner()
        job = self.job_source.get(job_id)
        oops = runner.runJobHandleError(job)
        if oops is None:
            oops_id = ''
        else:
            oops_id = oops.id
        return {'success': len(runner.completed_jobs), 'oops_id': oops_id}


class TwistedJobRunner(BaseJobRunner):
    """Run Jobs via twisted."""

    def __init__(self, job_source, dbuser, logger=None, error_utility=None):
        env = {'PATH': os.environ['PATH']}
        for name in ('PYTHONPATH', 'LPCONFIG'):
            if name in os.environ:
                env[name] = os.environ[name]
        starter = main.ProcessStarter(
            packages=('_pythonpath', 'twisted', 'ampoule'), env=env)
        super(TwistedJobRunner, self).__init__(logger, error_utility)
        self.job_source = job_source
        import_name = '%s.%s' % (
            removeSecurityProxy(job_source).__module__, job_source.__name__)
        self.pool = pool.ProcessPool(
            JobRunnerProcess, ampChildArgs=[import_name, str(dbuser)],
            starter=starter, min=0, timeout_signal=SIGHUP)

    def runJobInSubprocess(self, job):
        """Run the job_class with the specified id in the process pool.

        :return: a Deferred that fires when the job has completed.
        """
        job = IRunnableJob(job)
        try:
            job.acquireLease()
        except LeaseHeld:
            self.incomplete_jobs.append(job)
            return
        # Commit transaction to clear the row lock.
        transaction.commit()
        job_id = job.id
        deadline = timegm(job.lease_expires.timetuple())
        self.logger.debug(
            'Running %r, lease expires %s', job, job.lease_expires)
        # XXX: Need to somehow capture output here. This is the bit that
        # actually kicks off the subprocess stuff.
        deferred = self.pool.doWork(
            RunJobCommand, job_id = job_id, _deadline=deadline)

        def update(response):
            if response['success']:
                self.completed_jobs.append(job)
                self.logger.debug('Finished %r', job)
            else:
                self.incomplete_jobs.append(job)
                self.logger.debug('Incomplete %r', job)
            if response['oops_id'] != '':
                self._logOopsId(response['oops_id'])

        def job_raised(failure):
            self.incomplete_jobs.append(job)
            info = (failure.type, failure.value, failure.tb)
            oops = self._doOops(job, info)
            self._logOopsId(oops.id)
        deferred.addCallbacks(update, job_raised)
        return deferred

    def getTaskSource(self):
        """Return a task source for all jobs in job_source."""

        def producer():
            while True:
                jobs = list(self.job_source.iterReady())
                if len(jobs) == 0:
                    yield None
                for job in jobs:
                    yield lambda: self.runJobInSubprocess(job)
        return PollingTaskSource(5, producer().next)

    def doConsumer(self):
        """Create a ParallelLimitedTaskConsumer for this job type."""
        logger = logging.getLogger('gloop')
        logger.addHandler(logging.StreamHandler(sys.stdout))
        logger.setLevel(logging.DEBUG)
        consumer = ParallelLimitedTaskConsumer(1, logger=None)
        return consumer.consume(self.getTaskSource())

    def runAll(self):
        """Run all ready jobs, and any that become ready while running."""
        self.pool.start()
        d = defer.maybeDeferred(self.doConsumer)
        d.addCallbacks(self.terminated, self.failed)

    def terminated(self, ignored=None):
        """Callback to stop the processpool and reactor."""
        deferred = self.pool.stop()
        deferred.addBoth(lambda ignored: reactor.stop())

    def failed(self, failure):
        """Callback for when the job fails."""
        failure.printTraceback()
        self.terminated()

    @classmethod
    def runFromSource(cls, job_source, dbuser, logger):
        """Run all ready jobs provided by the specified source.

        The dbuser parameter is not ignored.
        """
        logger.info("Running through Twisted.")
        runner = cls(job_source, dbuser, logger)
        reactor.callWhenRunning(runner.runAll)
        handler = getsignal(SIGCHLD)
        try:
            reactor.run()
        finally:
            signal(SIGCHLD, handler)
        return runner


class JobCronScript(LaunchpadCronScript):
    """Base class for scripts that run jobs."""

    config_name = None

    def __init__(self, runner_class=JobRunner, test_args=None, name=None,
                 commandline_config=False):
        super(JobCronScript, self).__init__(
            name=name, dbuser=None, test_args=test_args)
        self._runner_class = runner_class
        if not commandline_config:
            return
        self.config_name = self.args[0]
        self.source_interface = import_source(
            self.config_section.source_interface)

    @property
    def dbuser(self):
        return self.config_section.dbuser

    @property
    def runner_class(self):
        """Enable subclasses to override with command-line arguments."""
        return self._runner_class

    def job_counts(self, jobs):
        """Return a list of tuples containing the job name and counts."""
        counts = defaultdict(lambda: 0)
        for job in jobs:
            counts[job.__class__.__name__] += 1
        return sorted(counts.items())

    @property
    def config_section(self):
        return getattr(config, self.config_name)

    def main(self):
        section = self.config_section
        if (getattr(section, 'error_dir', None) is not None
            and getattr(section, 'oops_prefix', None) is not None
            and getattr(section, 'copy_to_zlog', None) is not None):
            # If the three variables are not set, we will let the error
            # utility default to using the [error_reports] config.
            errorlog.globalErrorUtility.configure(self.config_name)
        job_source = getUtility(self.source_interface)
        runner = self.runner_class.runFromSource(
            job_source, self.dbuser, self.logger)
        for name, count in self.job_counts(runner.completed_jobs):
            self.logger.info('Ran %d %s jobs.', count, name)
        for name, count in self.job_counts(runner.incomplete_jobs):
            self.logger.info('%d %s jobs did not complete.', count, name)


class TimeoutError(Exception):

    def __init__(self):
        Exception.__init__(self, "Job ran too long.")
