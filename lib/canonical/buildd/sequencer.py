# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Launchpad build daemon job sequencer."""

__metaclass__ = type

from canonical.config import config
from twisted.internet import reactor, protocol

from twisted.mail.smtp import sendmail
from twisted.python import log

import time, os

# The message sent out in case of failure.
# Interpolated in BuildSequencer.mailOutFailure
failure_message = """From: Launchpad Build Daemon Sequencer <%(from)s>
To: %(to)s
Subject: Job %(job)s exited with code %(exitcode)d
X-Launchpad: yes
X-Buildd: yes

Job: %(job)s
Command: %(cmd)s
Exit code: %(exitcode)d
Standard Error:

%(errlog)s

Standard Output:

%(log)s
"""


class BuildSequencerJob(protocol.ProcessProtocol):
    """A job for the build sequencer to run."""

    def __init__(self, sequencer, conf_section):
        """Initialise a job from the provided config segment."""
        self.sequencer = sequencer
        self.name = conf_section.category_and_section_names[1]
        command = conf_section.command
        self.args = command.split()[1:]
        self.command = command.split()[0]
        self.delay = conf_section.mindelay
        self.forcelog = conf_section.alwayslog
        self.getCurrentTime = sequencer.getCurrentTime
        self.updateDue()

    def updateDue(self):
        """Update the due time to now+delay."""
        self.due = self.getCurrentTime() + self.delay

    def run(self):
        """Start this job running."""
        log.msg("Running " + self.name)
        self.log = ""
        self.errlog = ""
        reactor.spawnProcess(self, self.command, self.args, env=os.environ)

    def outReceived(self, data):
        """Pass on stdout data to the log."""
        self.log += data

    def errReceived(self, data):
        """Pass on stderr data to the log."""
        self.errlog += data

    def processEnded(self, statusobject):
        """Handle the job ending.

        If it was successful, we just reschedule. If it failed we need to
        process the log accordingly before rescheduling.
        """
        try:
            exit_code = statusobject.value.exitCode
            log.msg("Job %s completed with exit code %d" % (
                self.name, exit_code))
            if self.forcelog:
                log.msg("Job output was:\n%s\n" % self.log)
                log.msg("Job error output was:\n%s\n" % self.errlog)
            if exit_code != 0:
                # Non-zero exit code implies mailing someone...
                self.sequencer.mailOutFailure(exit_code, self)
            self.updateDue()
        finally:
            self.sequencer.scheduleCallback()


class BuildSequencer:
    """Serialise jobs for the launchpad build daemon network."""

    def __init__(self):
        """Construct a build sequencer."""
        self.callAfter = reactor.callLater
        self.getCurrentTime = time.time
        self.loadJobs()
        self.mailertargets = config.buildsequencer.mailproblemsto.split()
        log.msg("Mailer targets set to:")
        for target in self.mailertargets:
            log.msg("   ... " + target)

    def loadJobs(self):
        """Load the jobs from the configuration file"""
        self.jobs = []
        log.msg("Loading jobs...")
        for job in config.getByCategory('buildsequencer_job'):
            bsj = BuildSequencerJob(self, job)
            self.jobs.append(bsj)
            log.msg("   ...loaded " + bsj.name)

    def findEarliestJob(self):
        """Find the earliest job and return what it is, and when it's due."""
        earliest_job = self.jobs[0]
        for job in self.jobs[1:]:
            if job.due < earliest_job.due:
                earliest_job = job
        due_in = earliest_job.due - self.getCurrentTime()
        if due_in < 0:
            due_in = 0
        return (earliest_job, due_in)

    def scheduleCallback(self):
        """Schedule the next job to be run."""
        earliest_job, due_in = self.findEarliestJob()
        log.msg("Scheduling %s for %6.3g seconds time" % (
            earliest_job.name, due_in))
        self.callAfter(due_in, earliest_job.run)

    def interpolateFailureFor(self, recipient, exit_code, job):
        """Return the failure message interpolated with the relevant args."""
        return failure_message % {
            "from": config.buildsequencer.fromaddress,
            "to": recipient,
            "job": job.name,
            "exitcode": exit_code,
            "cmd": job.command,
            "log": job.log,
            "errlog": job.errlog
            }


    def mailOutFailure(self, exit_code, job):
        """Mail out the log and failure message for the given job."""

        for recipient in self.mailertargets:
            this_msg = self.interpolateFailureFor(recipient, exit_code, job)
            if recipient == "-":
                log.err(this_msg)
            else:
                log.msg("Mailing report to: " + recipient)
                d = sendmail(config.buildsequencer.smtphost,
                             config.buildsequencer.fromaddress,
                             recipient, this_msg)
                d.addErrback(log.err)
