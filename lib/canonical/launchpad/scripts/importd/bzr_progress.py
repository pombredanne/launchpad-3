# Copyright 2006 Canonical Ltd.  All rights reserved.
# Author: David Allouche <david@allouche.net>

"""Bzrlib progress reporting suitable for importd.

Importd has the following requirements for progress reporting.

 * Print lines as long as we are making progress. Importd will kill jobs that
   have not produced any output in ''some time'' (like 20 minutes), so if a job
   occasionally locks down, it does not end up blocking all the job slots. This
   safeguard has proven precious in the past.

 * Do not print too many lines, so we do not produce hundreds of megabytes of
   mindless muttering.

Printing 'tick' may be necessary if something runs for a long time without
giving more detailed messages, like 'update'.

In addition, the progress reporting should give useful information for the
operator to assess the progress of a job. If we just filter progress messages
to print one every interval, we get an aliasing effect and only uninformative
messages from highly-nested progress objects (or even ticks) are printed.

To limit the aliasing effect, we also print messages whose nesting level is
less than the previously printed message. Since, for a given Progress instance,
update messages are more informative than ticks, ticks are considered
fractionally more nested than updates at the same nesting level.

It would be possible to eliminate aliasing by delaying messages with a low
nesting level and printing them in place of the next more nested message. But
that would be more complicated, would make timestamps less accurate, and does
not seem necessary.
"""

__metaclass__ = type

__all__ = ['setup_batch_progress']


import time

from bzrlib.progress import DummyProgress
import bzrlib.ui

from canonical.codehosting import ProgressUIFactory


def setup_batch_progress():
    """Setup bzrlib to provide line-by-line progress."""
    bzrlib.ui.ui_factory = ProgressUIFactory(BatchProgress)


class BatchProgress(DummyProgress):
    """Progress-bar that gives simple line-by-line progress."""

    # This class derives from bzrlib's DummyProgress. To avoid clashing
    # with potential "_protected" attributes in the base class, all internal
    # attributes introduced here are "__private". -- David Allouche 2006-12-14

    __printer = None

    def __init__(self, *args, **kwargs):
        DummyProgress.__init__(self, *args, **kwargs)
        self.__level = 0

        # Since bzrlib sometimes create multiple top-level Progress instances
        # (that's a bug when it does), all BatchProgress instances delegate
        # printing to the same BatchProgressPrinter instance, so it can
        # effectively implement rate-limiting. -- David Allouche 2006-12-14
        if BatchProgress.__printer is None:
            BatchProgress.__printer = BatchProgressPrinter()

    def update(self, msg, current=None, total=None):
        self.__printer.update(self.__level, msg, current, total)

    def note(self, fmt_string, *args, **kwargs):
        self.__printer.print_(fmt_string % args)

    def tick(self):
        self.__printer.tick(self.__level)

    def child_progress(self, **kwargs):
        child = BatchProgress(**kwargs)
        child.__level = self.__level + 1
        return child


class BatchProgressPrinter:
    """Print rate-limited progress messages.

    See the module docstring for an explanation of the rate-limiting logic in
    this class.
    """

    # Avoid printing messages more than once every 'period' seconds.
    # Setting to 0 prints all messages.
    period = 10

    def __init__(self):
        self._last_time = self._now()
        self._last_level = 0
        self._current_level = None

    def _now(self):
        return time.time()

    def _should_print(self):
        if self._now() - self._last_time >= self.period:
            return True
        elif self._current_level < self._last_level:
            return True
        else:
            return False

    def print_(self, msg):
        """Inconditionally print a message."""
        print msg

    def _print_maybe(self, msg, *args):
        if not self._should_print():
            return
        if int(self._current_level):
            level = '+' * int(self._current_level) + ' '
        else:
            level = ''
        self.print_(level + msg % args)
        self._last_level = self._current_level
        self._last_time = self._now()

    def update(self, level, msg, current, total):
        """Maybe print an 'update' message.

        :param level: nesting level of the calling BatchProgress instance.
        :param msg: update message (passed by bzrlib).
        :param current: current step in this progress (passed by bzrlib).
        :param total: total steps in this progress (passed by bzrlib).
        """
        self._current_level = level
        if current is None and total is None:
            self._print_maybe(msg)
        elif total is None:
            assert current is not None
            self._print_maybe('%d %s', current, msg)
        else:
            assert current is not None
            self._print_maybe('%d/%d %s', current, total, msg)

    def tick(self, level):
        """Maybe print a 'tick' message.

        :param level: nesting level of the calling BatchProgress instance.
        """
        self._current_level = level + 0.5
        self._print_maybe('tick')
