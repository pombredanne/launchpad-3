#! /usr/bin/python

# Licenced under the GPL.
# Derived from BuildBot's slavecommand.py.
# Copyright (c) 2004 Virtual Development
# Author : Robert Collins <robertc@robertcollins.net>

import os, os.path, re, signal, shutil, types

from twisted.internet.defer import Deferred
from twisted.internet import reactor, threads
from twisted.python import log, failure, runtime
from twisted.spread import pb, jelly

from buildbot.slavecommand import Command
from importd.Job import CopyJob
from buildbot.process.step import FAILURE,WARNINGS,SUCCESS,SKIPPED


class ImportDJobCommand(Command):
    """This is a Command which runs a method on a Job object. The Job object ins
    Jellyified by the pb framework. The args dict contains
    the following keys:

     ['job'] (required): a job object.
     ['method'] (required): a method to run on the job object.
     ['args'] (optional): args to pass to the method.
     ['dir']: a directory (relative to the builder dir) to run the command in
     #['not_really']: 1 to skip execution, return rc==0
     #['timeout']: seconds of silence to tolerate before killing command

    ImportDJobCommand creates the following status messages:
     {'stdout': data} : when stdout data is available
     {'stderr': data} : when stderr data is available
     {'rc': rc} : when the process has terminated
     
    
    """

    def __init__(self, builder, args):
        Command.__init__(self, builder, args)
        self.job = args['job']
	self.method = args['method']
	self.args = args['args']
	self.kwargs = args.get('kwargs',{})
        self.want_stdout = args.get('want_stdout', 1)
        self.want_stderr = args.get('want_stderr', 1)
        # 'dir' is relative to Builder directory
        cmddir = args.get('dir', ".")
        if cmddir == None:
            self.dir = self.builder.basedir
        else:
            self.dir = os.path.join(self.builder.basedir, cmddir)
	self.kwargs['dir']=self.dir

    def __repr__(self):
        return "<importd.buildbot_slavecommand.ImportDJoblCommand '%s.%s'>" % (self.job,self.method)

    def record_stdout(self, message):
        reactor.callFromThread(self.sendStatus, {'stdout':message})
    
    def start(self):
        os.umask(0022)
        msg = "method '%s' with args %s , kwargs %s [%s]" % (self.method,
                                               self.args,
					       self.kwargs,
                                               self.stepId)
        log.msg("  " + msg)
        self.sendStatus({'header': msg+"\n"})
	result = None
        boundmethod=getattr(self.job,self.method)
        import logging
        from importd import LogAdaptor
        self.adaptor=LogAdaptor(self.record_stdout)
        jobname=os.path.basename(self.job.name)
        self.logger=logging.getLogger(jobname)
        self.logger.setLevel(logging.WARNING)
        self.logger.addHandler(self.adaptor)
        self.job.setJobTrigger(self.threadedJobBuildTrigger)
        self.kwargs['logger']=self.logger
        deferred = threads.deferToThread(boundmethod, *self.args, **self.kwargs)
        deferred.addCallback(self.finished)
        deferred.addErrback(self.failed)
	#result = eval("self.job.%s(*self.args, **self.kwargs)" % self.method)
	# what to do with result? 
        # todo send event based on the result.
	#reactor.callLater(1, self.finished, result)

    def threadedJobBuildTrigger(self, name):
        """Request the botmaster to run a build, from another thread.

        :param name: name of the builder to run.
        :type name: str
        """
        reactor.callFromThread(self.jobBuildTrigger, name)

    def jobBuildTrigger(self, name):
        """Request the botmaster to run a build, from the io thread.

        :param name: name of the builder to run
        :type name: str
        """
        d = self.builder.remote.callRemote("triggerBuild", name)
        d.addCallback(self.jobBuildTriggerOk, name)
        d.addErrback(self.jobBuildTriggerFailed, name)

    def jobBuildTriggerOk(self, result, name):
        """Callback for triggerBuild remote request."""
        self.logger.warning("Successful build request for %r: %r",
                            name, result)

    def jobBuildTriggerFailed(self, result, name):
        """Errback for triggerBulid remote request."""
        self.logger.error("FAILED build request for %r: %r", name, result)

    def finished(self, result):
        self.job.setJobTrigger(None)
        self.cleanUpLogging()
        log.msg("method '%s' finished with result %s" % (self.method, result))
	if result == None: result = SUCCESS
	self.sendStatus({'result': result})
        self.commandComplete()

    def failed(self, what_failed):
        self.cleanUpLogging()
        log.msg("method '%s' failed : '%s'" % (self.method, what_failed))
        self.sendStatus({'stderr': "%s" % what_failed})
        self.sendStatus({'result': FAILURE})
        self.commandFailed(failure.Failure(what_failed))

    def cleanUpLogging(self):
        """remove the logging adaptor from the logger, before we go away"""
        self.logger.removeHandler(self.adaptor)

class RemoteJob(pb.RemoteCopy, CopyJob):
	pass
	
pb.setUnjellyableForClass(CopyJob, RemoteJob)
