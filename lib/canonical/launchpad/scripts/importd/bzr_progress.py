# Copyright 2006 Canonical Ltd.  All rights reserved.
# Author: David Allouche <david@allouche.net>

"""Utilities to change the bzrlib progress reporting."""

__metaclass__ = type

__all__ = ['setup_batch_progress']

from bzrlib.progress import DummyProgress
import bzrlib.ui
from bzrlib.ui import SilentUIFactory


class BatchProgress(DummyProgress):
    """Progress-bar that gives simple line-by-line progress."""

    def update(self, msg, current=None, total=None):
        if current is None and total is None:
            print msg
        elif total is None:
            assert current is not None
            print '%d %s' % (current, msg)
        else:
            assert current is not None
            print '%d/%d %s' % (current, total, msg)

    def note(self, fmt_string, *args, **kwargs):
        self.update(fmt_string % args)


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
