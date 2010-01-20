# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Facilities for running Jobs."""


from __future__ import with_statement
__metaclass__ = type


__all__ = [
    'BaseRunnableJob',
    'JobRunner',
    'JobRunnerProcess',
    ]


import contextlib
import os
from signal import getsignal, SIGCHLD, SIGHUP, signal
import sys

from ampoule import child, pool, main
from twisted.internet import defer, error, reactor, stdio
from twisted.protocols import amp
from twisted.python import log, reflect

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.twistedsupport.task import (
    ParallelLimitedTaskConsumer, PollingTaskSource)
from lazr.delegates import delegates
import transaction

from lp.services.scripts.base import LaunchpadCronScript
from lp.services.job.interfaces.job import LeaseHeld, IRunnableJob, IJob
from lp.services.mail.sendmail import MailController
from canonical.launchpad import scripts
from canonical.launchpad.webapp import errorlog


class BaseRunnableJob:
    """Base class for jobs to be run via JobRunner.

    Derived classes should implement IRunnableJob, which requires implementing
    IRunnableJob.run.  They should have a `job` member which implements IJob.

    Subclasses may provide getOopsRecipients, to send mail about oopses.
    If so, they should also provide getOperationDescription.
    """
    delegates(IJob, 'job')

    user_error_types = ()

    def getOopsRecipients(self):
        """Return a list of email-ids to notify about oopses."""
        return self.getErrorRecipients()

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
        self.logger = logger
        self.error_utility = error_utility
        if self.error_utility is None:
            self.error_utility = errorlog.globalErrorUtility

    def runJob(self, job):
        """Attempt to run a job, updating its status as appropriate."""
        job = IRunnableJob(job)
        try:
            job.start()
            transaction.commit()
            job.run()
        except Exception:
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
                self.runJob(job)
            except job.user_error_types, e:
                job.notifyUserError(e)
            except Exception:
                info = sys.exc_info()
                return self._doOops(job, info)

    def _doOops(self, job, info):
        """Report an OOPS for the provided job and info.

        :param job: The IRunnableJob whose run failed.
        :param info: The standard sys.exc_info() value.
        :return: the Oops that was reported.
        """
        self.error_utility.raising(info)
        oops = self.error_utility.getLastOopsReport()
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
    def runFromSource(cls, job_source, logger):
        """Run all ready jobs provided by the specified source."""
        with removeSecurityProxy(job_source.contextManager()):
            logger.info("Running synchronously.")
            runner = cls.fromReady(job_source, logger)
            runner.runAll()
        return runner

    def runAll(self):
        """Run all the Jobs for this JobRunner."""
        for job in self.jobs:
            job = IRunnableJob(job)
            try:
                job.acquireLease()
            except LeaseHeld:
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


class JobRunnerProcess(child.AMPChild):
    """Base class for processes that run jobs."""

    def __init__(self):
        child.AMPChild.__init__(self)
        self.context_manager = self.job_class.contextManager()

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
        """Run a job of this job_class according to its job id."""
        runner = BaseJobRunner()
        job = self.job_class.get(job_id)
        oops = runner.runJobHandleError(job)
        if oops is None:
            oops_id = ''
        else:
            oops_id = oops.id
        return {'success': len(runner.completed_jobs), 'oops_id': oops_id}


class HUPProcessPool(pool.ProcessPool):
    """A ProcessPool that kills with HUP."""

    def _handleTimeout(self, child):
        try:
            child.transport.signalProcess(SIGHUP)
        except error.ProcessExitedAlready:
            pass


class TwistedJobRunner(BaseJobRunner):
    """Run Jobs via twisted."""

    def __init__(self, job_source, job_amp, logger=None, error_utility=None):
        starter = main.ProcessStarter(
            bootstrap=BOOTSTRAP, packages=('twisted', 'ampoule'),
            env={'PYTHONPATH': os.environ['PYTHONPATH'],
            'PATH': os.environ['PATH'],
            'LPCONFIG': os.environ['LPCONFIG']})
        super(TwistedJobRunner, self).__init__(logger, error_utility)
        self.job_source = job_source
        self.pool = HUPProcessPool(job_amp, starter=starter, min=0)

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
        job_id = job.id
        timeout = job.getTimeout()
        # work around ampoule bug
        if timeout == 0:
            timeout = 0.0000000000001
        deferred = self.pool.doWork(
            RunJobCommand, job_id = job_id, _timeout=timeout)
        def update(response):
            if response['success']:
                self.completed_jobs.append(job)
            else:
                self.incomplete_jobs.append(job)
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
                for job in self.job_source.iterReady():
                    yield lambda: self.runJobInSubprocess(job)
                yield None
        return PollingTaskSource(5, producer().next)

    def doConsumer(self):
        """Create a ParallelLimitedTaskConsumer for this job type."""
        consumer = ParallelLimitedTaskConsumer(1)
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
    def runFromSource(cls, job_source, logger, error_utility=None):
        """Run all ready jobs provided by the specified source."""
        logger.info("Running through Twisted.")
        runner = cls(job_source, removeSecurityProxy(job_source).amp, logger,
                     error_utility)
        reactor.callWhenRunning(runner.runAll)
        handler = getsignal(SIGCHLD)
        try:
            reactor.run()
        finally:
            signal(SIGCHLD, handler)
        return runner


class JobCronScript(LaunchpadCronScript):
    """Base class for scripts that run jobs."""

    def __init__(self, runner_class=JobRunner):
        dbuser = getattr(config, self.config_name).dbuser
        super(JobCronScript, self).__init__(self.config_name, dbuser)
        self.runner_class = runner_class

    def main(self):
        job_source = getUtility(self.source_interface)
        runner = self.runner_class.runFromSource(job_source, self.logger)
        self.logger.info(
            'Ran %d %s jobs.',
            len(runner.completed_jobs), self.source_interface.__name__)
        self.logger.info(
            '%d %s jobs did not complete.',
            len(runner.incomplete_jobs), self.source_interface.__name__)


class TimeoutError(Exception):

    def __init__(self):
        Exception.__init__(self, "Job ran too long.")


BOOTSTRAP = """\
import sys
from twisted.application import reactors
reactors.installReactor(sys.argv[-2])
from lp.services.job.runner import bootstrap
bootstrap(sys.argv[-1])
"""

def bootstrap(ampChildPath):
    def handler(signum, frame):
        raise TimeoutError
    signal(SIGHUP, handler)
    log.startLogging(sys.stderr)
    ampChild = reflect.namedAny(ampChildPath)
    stdio.StandardIO(ampChild(), 3, 4)
    scripts.execute_zcml_for_scripts(use_web_security=False)
    reactor.run()
