# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Profile requests when enabled."""

__all__ = []

__metaclass__ = type

from datetime import datetime
import os
import threading

from bzrlib.lsprof import BzrProfiler
from zope.error.interfaces import IErrorReportingUtility
from zope.component import getUtility

from canonical.config import config
import canonical.launchpad.webapp.adapter as da
from canonical.mem import memory, resident


class ProfilingOops(Exception):
    """Fake exception used to log OOPS information when profiling pages."""


_profilers = threading.local()


def start_request(event):
    """Handle profiling.

    If profiling is enabled, start a profiler for this thread. If memory
    profiling is requested, save the VSS and RSS.
    """
    if not config.profiling.profiling_allowed:
        return

    if (request_should_be_profiled(event.request) or
        config.profiling.profile_all_requests):
        _profilers.profiler = BzrProfiler()
        _profilers.profiler.start()
    else:
        _profilers.profiler = None

    if config.profiling.memory_profile_log:
        _profilers.memory_profile_start = (memory(), resident())


def end_request(event):
    """If profiling is turned on, save profile data for the request."""
    if not config.profiling.profiling_allowed:
        return

    request = event.request
    # Create a timestamp including milliseconds.
    now = datetime.fromtimestamp(da.get_request_start_time())
    timestamp = "%s.%d" % (
        now.strftime('%Y-%m-%d_%H:%M:%S'), int(now.microsecond/1000.0))
    pageid = request._orig_env.get('launchpad.pageid', 'Unknown')
    oopsid = getattr(request, 'oopsid', None)

    if _profilers.profiler is not None:
        profiler = _profilers.profiler
        _profilers.profiler = None
        prof_stats = profiler.stop()

        if oopsid is None:
            # Log an OOPS to get a log of the SQL queries, and other
            # useful information,  together with the profiling
            # information.
            info = (ProfilingOops, None, None)
            error_utility = getUtility(IErrorReportingUtility)
            error_utility.raising(info, request)
            oopsid = request.oopsid
        filename = '%s-%s-%s-%s.prof' % (
            timestamp, pageid, oopsid,
            threading.currentThread().getName())

        dump_path = os.path.join(config.profiling.profile_dir, filename)
        prof_stats.save(dump_path, format="callgrind")

        # Free some memory.
        _profilers.profiler = None

    # Dump memory profiling info.
    if config.profiling.memory_profile_log:
        log = file(config.profiling.memory_profile_log, 'a')
        vss_start, rss_start = _profilers.memory_profile_start
        vss_end, rss_end = memory(), resident()
        if oopsid is None:
            oopsid = '-'
        log.write('%s %s %s %f %d %d %d %d\n' % (
            timestamp, pageid, oopsid, da.get_request_duration(),
            vss_start, rss_start, vss_end, rss_end))
        log.close()


def request_should_be_profiled(request):
    """Should we turn on profiling for the given request object?"""
    return ('++profile++' in request.get('PATH_INFO'))
