# Copyright 2006 Canonical Ltd.  All rights reserved.
# Author: David Allouche <david@allouche.net>

"""Utilities to change the bzrlib progress reporting."""

__metaclass__ = type

__all__ = ['setup_batch_progress']


import time

from bzrlib.progress import DummyProgress
import bzrlib.ui
from bzrlib.ui import SilentUIFactory


class BatchProgress(DummyProgress):
    """Progress-bar that gives simple line-by-line progress."""

    __printer = None

    def __init__(self, *args, **kwargs):
        DummyProgress.__init__(self, *args, **kwargs)
        self.__level = 0

    def __get_printer(self):
        if self.__printer is None:
            BatchProgress.__printer = BatchProgressPrinter()
        return self.__printer

    def update(self, msg, current=None, total=None):
        self.__get_printer().update(self.__level, msg, current, total)

    def note(self, fmt_string, *args, **kwargs):
        self.__get_printer().print_(fmt_string % args)

    def tick(self):
        self.__get_printer().tick(self.__level)

    def child_progress(self, **kwargs):
        child = BatchProgress(**kwargs)
        child.__level = self.__level + 1
        return child


class BatchProgressPrinter:

    # Avoid printing messages more than once every 'period' seconds.
    # Setting to 0 prints all messages.
    period = 10

    def __init__(self):
        self.last_time = self.now()
        self.last_level = 0
        self.current_level = None

    def now(self):
        return time.time()

    def should_print(self):
        if self.now() - self.last_time >= self.period:
            return True
        elif self.current_level < self.last_level:
            return True
        else:
            return False

    def print_(self, msg):
        print msg

    def print_maybe(self, msg, *args):
        if not self.should_print():
            return
        if int(self.current_level):
            level = '+' * int(self.current_level) + ' '
        else:
            level = ''
        self.print_(level + msg % args)
        self.last_level = self.current_level
        self.last_time = self.now()

    def update(self, level, msg, current, total):
        self.current_level = level
        if current is None and total is None:
            self.print_maybe(msg)
        elif total is None:
            assert current is not None
            self.print_maybe('%d %s', current, msg)
        else:
            assert current is not None
            self.print_maybe('%d/%d %s', current, total, msg)

    def tick(self, level):
        self.current_level = level + 0.5
        self.print_maybe('tick')


class BatchUIFactory(SilentUIFactory):
    """A UI Factory that prints line-by-line progress."""

    def progress_bar(self):
        return BatchProgress()

    def nested_progress_bar(self):
        if self._progress_bar_stack is None:
            self._progress_bar_stack = bzrlib.progress.ProgressBarStack(
                klass=BatchProgress)
        return self._progress_bar_stack.get_nested()


def setup_batch_progress():
    """Setup bzrlib to provide line-by-line progress."""
    bzrlib.ui.ui_factory = BatchUIFactory()
