# Copyright 2009 Canonical Ltd.  All rights reserved.

"""XXX."""

__metaclass__ = type
__all__ = []


import sys
import time

from bzrlib.ui import UIFactory


class LoggingUIFactory(UIFactory):
    """A UI Factory that produces reasonably sparse logging style output.

    """

    def __init__(self, time_source=time.time, output=None, interval=60.0):
        UIFactory.__init__(self)
        self.time_source = time_source
        self._last_update = 0
        self._last_updated_task = None
        self._bytes_since_last_update = 0
        if output is None:
            self.output = sys.stdout
        else:
            self.output = output
        self.interval = interval

    def _cur_task(self):
        if self._task_stack:
            return self._task_stack[-1]
        else:
            return None

    def show(self, msg):
        self.output.write(msg + '\n')
        self._last_updated_task = self._cur_task()
        self._last_update = self.time_source()
        self._bytes_since_last_update = 0

    def _should_update(self):
        if (self.time_source() - self._last_update > self.interval
            or self._cur_task() != self._last_updated_task):
            return True
        else:
            return False

    def timestamp(self):
        return time.strftime(
            '[%Y:%m:%d %H:%M:%S]', time.gmtime(self.time_source()))

    def _format_task(self, task):
        # Stolen from bzrlib.ui.text.TextProgressView
        if not task.show_count:
            s = ''
        elif task.current_cnt is not None and task.total_cnt is not None:
            s = ' %d/%d' % (task.current_cnt, task.total_cnt)
        elif task.current_cnt is not None:
            s = ' %d' % (task.current_cnt)
        else:
            s = ''
        # compose all the parent messages
        t = task
        m = task.msg
        while t._parent_task:
            t = t._parent_task
            if t.msg:
                m = t.msg + ':' + m
        return '%s %s'%(self.timestamp(), m + s)

    def _progress_finished(self, task):
        """See `UIFactory._progress_finished`."""
        UIFactory._progress_finished(self, task)
        self.show(self._format_task(task))

    def _progress_updated(self, task):
        """See `UIFactory._progress_updated`."""
        if self._should_update():
            self.show(self._format_task(task))

    def report_transport_activity(self, transport, byte_count, direction):
        """See `UIFactory.report_transport_activitys`."""
        self._bytes_since_last_update += byte_count
        if self._should_update():
            self.show("%s bytes transferred" % self._bytes_since_last_update)
