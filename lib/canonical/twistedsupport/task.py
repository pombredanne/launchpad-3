# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tools for managing long-running or difficult tasks with Twisted."""

__metaclass__ = type
__all__ = [
    'AlreadyRunningError',
    'ITaskConsumer',
    'ITaskSource',
    'ParallelLimitedTaskConsumer',
    'PollingTaskSource',
    ]

from twisted.internet import defer
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
from twisted.python import log

from zope.interface import implements, Interface


class ITaskSource(Interface):
    """A source of tasks to do."""

    def start(task_consumer):
        """Start generating tasks.

        If `start` has already been called, then the given 'task_consumer'
        replaces the existing task accepter.

        :param task_consumer: A provider of `ITaskConsumer`.
        """

    def stop():
        """Stop generating tasks.

        Any subsequent calls to `stop` are silently ignored.
        """


class ITaskConsumer(Interface):
    """A consumer of tasks. Pass to an `ITaskSource` provider.

    Note that implementations of `ITaskConsumer` need to provide their own way
    of getting references to ITaskSources.
    """

    def taskStarted(task):
        """Called when the task source generates a task.

        This is a throw-it-over-the-wall interface used by ITaskSource.
        ITaskSource expects it to finish quickly and to not raise errors. Any
        return value is completely ignored.

        :param task: The interface for this is defined by the task source.
        """

    def taskProductionFailed(reason):
        """Called when the task source fails to produce a task.

        :param reason: A `twisted.python.failure.Failure` object.
        """


class AlreadyRunningError(Exception):
    """Raised when we try to start a consumer that's already running."""

    def __init__(self, consumer, source):
        Exception.__init__(
            self, "%r is already consuming tasks from %r."
            % (consumer, source))


class NotRunningError(Exception):
    """Raised when we try to run tasks on a consumer before it has started."""

    def __init__(self, consumer):
        Exception.__init__(
            self, "%r has not started, cannot run tasks." % (consumer,))


class PollingTaskSource:
    """A task source that polls to generate tasks.

    Useful for systems where we need to poll a central server in order to find
    new work to do.
    """

    implements(ITaskSource)

    def __init__(self, interval, task_producer, clock=None):
        """Construct a `PollingTaskSource`.

        Polls 'task_producer' every 'interval' seconds. 'task_producer' returns
        either None if there's no work to do right now, or some representation
        of the task which is passed to the 'task_consumer' callable given to
        `start`.

        :param interval: The length of time between polls in seconds.
        :param task_producer: The polling mechanism. This is a nullary
            callable that can return a Deferred. See above for more details.
        :param clock: An `IReactorTime` implementation that we use to manage
            the interval-based polling. Defaults to using the reactor (i.e.
            actual time).
        """
        self._interval = interval
        self._task_producer = task_producer
        if clock is None:
            clock = reactor
        self._clock = clock
        self._looping_call = None

    def start(self, task_consumer):
        """See `ITaskSource`."""
        # XXX: maybe interval should be passed here
        self.stop()
        self._looping_call = LoopingCall(self._poll, task_consumer)
        self._looping_call.clock = self._clock
        self._looping_call.start(self._interval)

    def _poll(self, task_consumer):
        """Poll for tasks, passing them to 'task_consumer'."""
        def got_task(task):
            if task is not None:
                # Note that we deliberately throw away the return value. The
                # task and the consumer need to figure out how to get output
                # back to the end user.
                task_consumer.taskStarted(task)
        d = defer.maybeDeferred(self._task_producer)
        d.addCallbacks(got_task, task_consumer.taskProductionFailed)

    def stop(self):
        """See `ITaskSource`."""
        if self._looping_call is not None:
            self._looping_call.stop()
            self._looping_call = None


class ParallelLimitedTaskConsumer:
    """A consumer that runs tasks with limited parallelism.

    Assumes that the task source generates tasks that are nullary callables
    that might return `Deferred`s.
    """

    implements(ITaskSource)

    def __init__(self, worker_limit):
        self._task_source = None
        self._worker_limit = worker_limit
        self._worker_count = 0
        self._terminationDeferred = None

    def consume(self, task_source):
        """Start consuing tasks from 'task_source'.

        :param task_source: An `ITaskSource` provider.
        :return: A `Deferred` that fires when the task source is exhausted
            and we are not running any tasks.
        """
        if self._task_source is not None:
            raise AlreadyRunningError(self, self._task_source)
        self._task_source = task_source
        self._terminationDeferred = defer.Deferred()
        task_source.start(self)
        return self._terminationDeferred

    def taskStarted(self, task):
        """See `ITaskSource`."""
        if self._task_source is None:
            raise NotRunningError(self)
        self._worker_count += 1
        if self._worker_count >= self._worker_limit:
            self._task_source.stop()
        task()
        self._taskEnded()

    def taskProductionFailed(self, reason):
        """See `ITaskSource`."""
        raise NotRunningError(self)

    def _taskEnded(self):
        self._worker_count -= 1
        if self._worker_count == 0:
            self._terminationDeferred.callback(None)


class OldParallelLimitedTaskSink:
    """ """

    def __init__(self, worker_limit, task_source):
        self.worker_limit = worker_limit
        self.worker_count = 0
        self.task_source = task_source

    def start(self):
        self._terminationDeferred = defer.Deferred()
        self.task_source.start(self.acceptTask)
        return self._terminationDeferred

    def acceptTask(self, task):
        self.worker_count += 1
        if self.worker_count >= self.worker_limit:
            self.task_source.stop()
        d = task.run()
        # We don't expect these tasks to have interesting return values or
        # failure modes.
        d.addErrback(log.err)
        d.addCallback(self.taskEnded)

    def taskEnded(self, ignored):
        self.worker_count -= 1
        if self.worker_count == 0:
            self._terminationDeferred.callback(None)
        if self.worker_count < self.worker_limit:
            self.start()
