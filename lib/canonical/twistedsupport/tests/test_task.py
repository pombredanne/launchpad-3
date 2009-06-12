# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for our task support."""

__metaclass__ = type

import unittest

from twisted.internet.defer import Deferred
from twisted.internet.task import Clock

from zope.interface import implements

from canonical.twistedsupport.task import (
    AlreadyRunningError, ITaskConsumer, ITaskSource, NotRunningError,
    ParallelLimitedTaskConsumer, PollingTaskSource)
from lp.testing import TestCase


class NoopTaskConsumer:

    implements(ITaskConsumer)

    def taskStarted(self, task):
        """Do nothing."""

    def taskProductionFailed(self, reason):
        """Do nothing."""


class AppendingTaskConsumer:

    implements(ITaskConsumer)

    def __init__(self, data_sink):
        self.data_sink = data_sink

    def taskStarted(self, task):
        """Do nothing."""
        self.data_sink.append(task)

    def taskProductionFailed(self, reason):
        """Do nothing."""


class LoggingSource:

    implements(ITaskSource)

    def __init__(self, log):
        self._log = log

    def start(self, consumer):
        self._log.append(('start', consumer))

    def stop(self):
        self._log.append('stop')


class TestPollingTaskSource(TestCase):
    """Tests for `PollingTaskSource`."""

    def setUp(self):
        TestCase.setUp(self)
        self._num_task_producer_calls = 0
        self._default_task_consumer = NoopTaskConsumer()

    def _default_task_producer(self):
        self._num_task_producer_calls += 1
        return None

    def makeTaskSource(self, task_producer=None, interval=None, clock=None):
        if task_producer is None:
            task_producer = self._default_task_producer
        if clock is None:
            clock = Clock()
        if interval is None:
            interval = self.factory.getUniqueInteger()
        return PollingTaskSource(interval, task_producer, clock=clock)

    def test_provides_ITaskSource(self):
        # PollingTaskSource instances provide ITaskSource.
        self.assertProvides(self.makeTaskSource(), ITaskSource)

    def test_start_commences_polling(self):
        # Calling `start` on a PollingTaskSource begins polling the task
        # factory.
        task_source = self.makeTaskSource()
        task_source.start(self._default_task_consumer)
        self.assertEqual(1, self._num_task_producer_calls)

    def test_start_continues_polling(self):
        # Calling `start` on a PollingTaskSource begins polling the task
        # factory. This polling continues over time, once every 'interval'
        # seconds.
        clock = Clock()
        interval = self.factory.getUniqueInteger()
        task_source = self.makeTaskSource(interval=interval, clock=clock)
        task_source.start(self._default_task_consumer)
        self._num_task_producer_calls = 0
        clock.advance(interval)
        self.assertEqual(1, self._num_task_producer_calls)

    def test_stop_stops_polling(self):
        # Calling `stop` after a PollingTaskSource has started will stop the
        # polling.
        clock = Clock()
        interval = self.factory.getUniqueInteger()
        task_source = self.makeTaskSource(interval=interval, clock=clock)
        task_source.start(self._default_task_consumer)
        task_source.stop()
        self._num_task_producer_calls = 0
        clock.advance(interval)
        # No more calls were made.
        self.assertEqual(0, self._num_task_producer_calls)

    def test_start_multiple_times_polls_immediately(self):
        # Starting a task source multiple times polls immediately.
        clock = Clock()
        interval = self.factory.getUniqueInteger()
        task_source = self.makeTaskSource(interval=interval, clock=clock)
        task_source.start(self._default_task_consumer)
        clock.advance(interval / 2.0)
        self._num_task_producer_calls = 0
        task_source.start(self._default_task_consumer)
        self.assertEqual(1, self._num_task_producer_calls)

    def test_start_multiple_times_resets_polling_loop(self):
        # Starting a task source multiple times resets the polling loop to
        # start from now.
        clock = Clock()
        interval = self.factory.getUniqueInteger()
        task_source = self.makeTaskSource(interval=interval, clock=clock)
        task_source.start(self._default_task_consumer)
        clock.advance(interval / 2.0)
        task_source.start(self._default_task_consumer)
        self._num_task_producer_calls = 0
        clock.advance(interval)
        self.assertEqual(1, self._num_task_producer_calls)

    def test_starting_again_changes_consumer(self):
        # Starting a task source again changes the task consumer.
        tasks = ['foo', 'bar']
        consumer1 = []
        consumer2 = []
        task_source = self.makeTaskSource(task_producer=iter(tasks).next)
        task_source.start(AppendingTaskConsumer(consumer1))
        task_source.start(AppendingTaskConsumer(consumer2))
        self.assertEqual(([tasks[0]], [tasks[1]]), (consumer1, consumer2))

    def test_task_consumer_called_when_factory_produces_task(self):
        # The task_consumer passed to start is called when the factory produces
        # a task.
        tasks = ['foo', 'bar']
        tasks_called = []
        task_source = self.makeTaskSource(task_producer=iter(tasks).next)
        task_source.start(AppendingTaskConsumer(tasks_called))
        self.assertEqual([tasks[0]], tasks_called)

    def test_task_consumer_not_called_when_factory_doesnt_produce(self):
        # The task_consumer passed to start is *not* called when the factory
        # returns None (implying there are no tasks to do right now).
        task_producer = lambda: None
        tasks_called = []
        task_source = self.makeTaskSource(task_producer=task_producer)
        task_source.start(AppendingTaskConsumer(tasks_called))
        self.assertEqual([], tasks_called)

    def test_stop_without_start(self):
        # Calling 'stop' before 'start' is called silently succeeds.
        task_source = self.makeTaskSource()
        # Assert that this doesn't raise an exception.
        task_source.stop()

    def test_stop_multiple_times(self):
        # Calling 'stop' multiple times has no effect.
        task_source = self.makeTaskSource()
        task_source.stop()
        # Assert that this doesn't raise an exception.
        task_source.stop()

    def test_producer_returns_deferred(self):
        # The task producer can return Deferreds. In this case, we only call
        # the consumer when the Deferred fires.
        deferred = Deferred()
        tasks_called = []
        task_source = self.makeTaskSource(task_producer=lambda: deferred)
        task_source.start(AppendingTaskConsumer(tasks_called))
        self.assertEqual([], tasks_called)
        deferred.callback('foo')
        self.assertEqual(['foo'], tasks_called)

    def test_producer_errors_call_taskProductionFailed(self):
        # If the producer raises an error, then we call taskProductionFailed
        # on the task consumer.
        class LoggingConsumer:
            def __init__(self):
                self._task_production_failed_calls = []
            def taskStarted(slf, task):
                self.fail("taskStarted should not be called.")
            def taskProductionFailed(self, reason):
                self._task_production_failed_calls.append(reason)

        task_source = self.makeTaskSource(task_producer=lambda: 1/0)
        consumer = LoggingConsumer()
        task_source.start(consumer)
        self.assertEqual(1, len(consumer._task_production_failed_calls))
        reason = consumer._task_production_failed_calls[0]
        self.assertTrue(reason.check(ZeroDivisionError))


class TestParallelLimitedTaskConsumer(TestCase):
    """Tests for `ParallelLimitedTaskConsumer`."""

    def makeConsumer(self, worker_limit=None):
        if worker_limit is None:
            # Unreasonably large number.
            worker_limit = 9999999
        return ParallelLimitedTaskConsumer(worker_limit=worker_limit)

    def test_implements_ITaskConsumer(self):
        # ParallelLimitedTaskConsumer instances provide ITaskConsumer.
        self.assertProvides(self.makeConsumer(), ITaskSource)

    def test_consume_starts_source(self):
        # Calling `consume` with a task source starts that source.
        consumer = self.makeConsumer()
        log = []
        source = LoggingSource(log)
        consumer.consume(source)
        self.assertEqual([('start', consumer)], log)

    def test_consume_twice_raises_error(self):
        # Calling `consume` twice always raises an error.
        consumer = self.makeConsumer()
        source = LoggingSource([])
        consumer.consume(source)
        self.assertRaises(AlreadyRunningError, consumer.consume, source)

    def test_consume_returns_deferred_doesnt_fire_until_tasks(self):
        # `consume` returns a Deferred that fires when no more tasks are
        # running, but only after we've actually done something.
        consumer = self.makeConsumer()
        log = []
        d = consumer.consume(LoggingSource([]))
        d.addCallback(log.append)
        self.assertEqual([], log)

    def test_consume_returns_deferred_fires_when_tasks_done(self):
        # `consume` returns a Deferred that fires when no more tasks are
        # running.
        consumer = self.makeConsumer()
        log = []
        d = consumer.consume(LoggingSource([]))
        d.addCallback(log.append)
        consumer.taskStarted(lambda: None)
        self.assertEqual([None], log)

    def test_taskStarted_before_consume_raises_error(self):
        # taskStarted can only be called after we have started consuming. This
        # is because taskStarted might need to stop task production to avoid a
        # work overload.
        consumer = self.makeConsumer()
        self.assertRaises(NotRunningError, consumer.taskStarted, None)

    def test_taskProductionFailed_before_consume_raises_error(self):
        # taskProductionFailed can only be called after we have started
        # consuming. This is because taskProductionFailed might need to stop
        # task production to handle errors properly.
        consumer = self.makeConsumer()
        self.assertRaises(
            NotRunningError, consumer.taskProductionFailed, None)

    def test_taskStarted_runs_task(self):
        # Calling taskStarted with a task runs that task.
        log = []
        consumer = self.makeConsumer()
        consumer.consume(LoggingSource([]))
        consumer.taskStarted(lambda: log.append('task'))
        self.assertEqual(['task'], log)

    def test_reaching_working_limit_stops_source(self):
        # Each time taskStarted is called, we start a worker. When we reach
        # the worker limit, we tell the source to stop generating work.
        worker_limit = 3
        consumer = self.makeConsumer(worker_limit=worker_limit)
        log = []
        source = LoggingSource(log)
        consumer.consume(source)
        del log[:]
        consumer.taskStarted(lambda: Deferred())
        self.assertEqual([], log)
        for i in range(worker_limit - 1):
            consumer.taskStarted(lambda: Deferred())
        self.assertEqual(['stop'], log)

    def test_passing_working_limit_stops_source(self):
        # If we have already reached the worker limit, and taskStarted is
        # called, we tell the source (again, presumably), to stop generating
        # work.
        worker_limit = 1
        consumer = self.makeConsumer(worker_limit=worker_limit)
        log = []
        source = LoggingSource(log)
        consumer.consume(source)
        del log[:]
        consumer.taskStarted(lambda: Deferred())
        # Reached the limit.
        self.assertEqual(['stop'], log)
        del log[:]
        # Passed the limit.
        consumer.taskStarted(lambda: Deferred())
        self.assertEqual(['stop'], log)

    def test_run_task_even_though_passed_limit(self):
        # If the source sends us work to do even though we've passed our
        # concurrency limit, we'll do the work anyway. We cannot rely on the
        # source sending us the work again.
        log = []
        def log_append(item):
            log.append(item)
            return Deferred()
        consumer = self.makeConsumer(worker_limit=1)
        consumer.consume(LoggingSource([]))
        consumer.taskStarted(lambda: log_append('task1'))
        consumer.taskStarted(lambda: log_append('task2'))
        self.assertEqual(['task1', 'task2'], log)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
