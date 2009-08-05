# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tools for managing long-running or difficult tasks with Twisted."""

__metaclass__ = type
__all__ = [
    'AlreadyRunningError',
    'ITaskConsumer',
    'ITaskSource',
    'NotRunningError',
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

        :return: A Deferred that will fire when the source is stopped.  It is
            possible that tasks may be produced until this deferred fires.
        """


class ITaskConsumer(Interface):
    """A consumer of tasks.

    Pass this to the 'start' method of an `ITaskSource` provider.

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

    def noTasksFound():
        """Called when no tasks were found."""

    def taskProductionFailed(reason):
        """Called when the task source fails to produce a task.

        :param reason: A `twisted.python.failure.Failure` object.
        """


class PollingTaskSource:
    """A task source that polls to generate tasks.

    This is useful for systems where we need to poll a central server in order
    to find new work to do.
    """

    implements(ITaskSource)

    def __init__(self, interval, task_producer, clock=None):
        """Construct a `PollingTaskSource`.

        Polls 'task_producer' every 'interval' seconds. 'task_producer'
        returns either None if there's no work to do right now, or some
        representation of the task which is passed to the 'task_consumer'
        callable given to `start`. 'task_producer' can also return a
        `Deferred`.

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
        self._lock = defer.succeed(None)

    def start(self, task_consumer):
        """See `ITaskSource`."""
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
            else:
                task_consumer.noTasksFound()
        def task_failed(reason):
            # If task production fails, we inform the consumer of this, but we
            # don't let any deferred it returns delay subsequent polls.
            task_consumer.taskProductionFailed(reason)
        d = defer.maybeDeferred(self._task_producer)
        self._lock = defer.Deferred()
        def release_lock(value):
            self._lock.callback(None)
            self._lock = defer.succeed(None)
            return value
        d.addBoth(release_lock)
        d.addCallbacks(got_task, task_failed)
        return d

    def stop(self):
        """See `ITaskSource`."""
        if self._looping_call is not None:
            self._looping_call.stop()
            self._looping_call = None
        d = defer.Deferred()
        self._lock.addCallback(d.callback)
        return d


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


class ParallelLimitedTaskConsumer:
    """A consumer that runs tasks with limited parallelism.

    Assumes that the task source generates tasks that are nullary callables
    that might return `Deferred`s.
    """

    implements(ITaskConsumer)

    def __init__(self, worker_limit):
        self._task_source = None
        self._worker_limit = worker_limit
        self._worker_count = 0
        self._terminationDeferred = None

    def consume(self, task_source):
        """Start consuming tasks from 'task_source'.

        :param task_source: An `ITaskSource` provider.
        :raise AlreadyRunningError: If 'consume' has already been called on
            this consumer.
        :return: A `Deferred` that fires when the task source is exhausted
            and we are not running any tasks.
        """
        if self._task_source is not None:
            raise AlreadyRunningError(self, self._task_source)
        self._task_source = task_source
        self._terminationDeferred = defer.Deferred()
        # This merely begins polling. This means that we acquire our initial
        # batch of work at the rate of one task per polling interval. As long
        # as the polling interval is small, this is probably OK.
        task_source.start(self)
        return self._terminationDeferred

    def taskStarted(self, task):
        """See `ITaskConsumer`.

        Stops the task source when we reach the maximum number of concurrent
        tasks.

        :raise NotRunningError: if 'consume' has not yet been called.
        """
        if self._task_source is None:
            raise NotRunningError(self)
        self._worker_count += 1
        if self._worker_count >= self._worker_limit:
            self._task_source.stop()
        d = defer.maybeDeferred(task)
        # We don't expect these tasks to have interesting return values or
        # failure modes.
        d.addErrback(log.err)
        d.addCallback(self._taskEnded)

    def noTasksFound(self):
        """See `ITaskConsumer`.

        Called when the producer found no tasks.  If we are not currently
        running any workers, exit.

        This will only actually happen if the very first production doesn't
        find any jobs, if we actually start any jobs then the exit condition
        in _taskEnded will always be reached before this one.
        """
        if self._worker_count == 0:
            self._terminationDeferred.callback(None)

    def taskProductionFailed(self, reason):
        """See `ITaskConsumer`.

        Called by the task source when a failure occurs while producing a
        task. When this happens, we stop the task source. Any currently
        running tasks will finish, and each time this happens, we'll ask the
        task source to start again.

        If the source keeps failing, we'll eventually have no tasks running,
        at which point we stop the source and fire the termination deferred,
        signalling the end of this run.

        This approach allows us to handle intermittent failures gracefully (by
        retrying the next time a task finishes), and to handle persistent
        failures well (by shutting down when there are no more tasks left).

        :raise NotRunningError: if 'consume' has not yet been called.
        """
        if self._task_source is None:
            raise NotRunningError(self)
        self._task_source.stop()
        if self._worker_count == 0:
            self._terminationDeferred.callback(None)

    def _taskEnded(self, ignored):
        """Handle a task reaching completion.

        Reduces the number of concurrent workers. If there are no running
        workers then we fire the termination deferred, signalling the end of
        the run.

        If there are available workers, we ask the task source to start
        producing jobs.
        """
        self._worker_count -= 1
        if self._worker_count == 0:
            self._task_source.stop()
            self._terminationDeferred.callback(None)
        elif self._worker_count < self._worker_limit:
            self._task_source.start(self)
        else:
            # We're over the worker limit, nothing we can do.
            pass
