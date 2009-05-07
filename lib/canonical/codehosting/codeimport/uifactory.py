# Copyright 2009 Canonical Ltd.  All rights reserved.

"""XXX."""

__metaclass__ = type
__all__ = ['LoggingUIFactory']


import sys
import time

from bzrlib.ui.text import TextUIFactory, TextProgressView


class LoggingUIFactory(TextUIFactory):
    """A UI Factory that produces reasonably sparse logging style output.
    """

    def __init__(self, bar_type=None, stdin=None, stdout=None, stderr=None,
                 time_source=time.time, writer=None, interval=60.0):
        TextUIFactory.__init__(self, bar_type, stdin, stdout, stderr)
        self.interval = interval
        self._progress_view = LoggingTextProgressView(
            time_source, writer, interval)

class LoggingTextProgressView(TextProgressView):

    def __init__(self, time_source, writer, interval):
        # If anything refers to _term_file, that's a bug for us.
        TextProgressView.__init__(self, term_file=None)
        self._writer = writer
        self.time_source = time_source
        if writer is None:
            self.write = sys.stdout.write
        else:
            self.write = writer
        self._transport_expire_time = 0
        self._update_repaint_frequency = interval
        self._transport_repaint_frequency = interval

    def _show_line(self, s):
        self._total_byte_count = 0
        self._transport_update_time = self.time_source()
        self._writer(s)

    def _render_bar(self):
        return ''

    def _format_transport_msg(self, scheme, dir_char, rate):
        return '%s bytes transferred' % self._total_byte_count

    # What's below *should* be in bzrlib, and will be soon.

    def show_progress(self, task):
        """Called by the task object when it has changed.

        :param task: The top task object; its parents are also included
            by following links.
        """
        must_update = task is not self._last_task
        self._last_task = task
        now = self.time_source()
        if (not must_update) and (now < self._last_repaint + self._update_repaint_frequency):
            return
        if now > self._transport_update_time + self._transport_expire_time:
            # no recent activity; expire it
            self._last_transport_msg = ''
        self._last_repaint = now
        self._repaint()

    def _show_transport_activity(self, transport, direction, byte_count):
        """Called by transports via the ui_factory, as they do IO.

        This may update a progress bar, spinner, or similar display.
        By default it does nothing.
        """
        # XXX: Probably there should be a transport activity model, and that
        # too should be seen by the progress view, rather than being poked in
        # here.
        self._total_byte_count += byte_count
        self._bytes_since_update += byte_count
        now = self.time_source()
        if self._transport_update_time is None:
            self._transport_update_time = now
        elif now >= (self._transport_update_time + self._transport_repaint_frequency):
            # guard against clock stepping backwards, and don't update too
            # often
            rate = self._bytes_since_update / (now - self._transport_update_time)
            scheme = getattr(transport, '_scheme', None) or repr(transport)
            if direction == 'read':
                dir_char = '>'
            elif direction == 'write':
                dir_char = '<'
            else:
                dir_char = '?'
            msg = self._format_transport_msg(scheme, dir_char, rate)
            self._transport_update_time = now
            self._last_repaint = now
            self._bytes_since_update = 0
            self._last_transport_msg = msg
            self._repaint()
