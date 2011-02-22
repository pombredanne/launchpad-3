# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Profile requests when enabled."""

__all__ = []

__metaclass__ = type

from datetime import datetime
import os
import threading
import StringIO

from bzrlib.lsprof import BzrProfiler
from chameleon.zpt.template import PageTemplateFile
from zope.app.publication.interfaces import IEndRequestEvent
from zope.component import (
    adapter,
    getUtility,
    )
from zope.contenttype.parse import parse
from zope.error.interfaces import IErrorReportingUtility
from zope.traversing.namespace import view

from canonical.config import config
import canonical.launchpad.webapp.adapter as da
from canonical.launchpad.webapp.interfaces import IStartRequestEvent
from lp.services.profile.mem import (
    memory,
    resident,
    )


class ProfilingOops(Exception):
    """Fake exception used to log OOPS information when profiling pages."""


_profilers = threading.local()


@adapter(IStartRequestEvent)
def start_request(event):
    """Handle profiling.

    If profiling is enabled, start a profiler for this thread. If memory
    profiling is requested, save the VSS and RSS.
    """
    if not config.profiling.profiling_allowed:
        return
    actions = get_desired_profile_actions(event.request)
    if config.profiling.profile_all_requests:
        actions.add('log')
    _profilers.actions = actions
    _profilers.profiler = None
    if actions:
        if actions.difference(('help', )):
            # If this assertion has reason to fail, we'll need to add code
            # to try and stop the profiler before we delete it, in case it is
            # still running.
            assert getattr(_profilers, 'profiler', None) is None
            _profilers.profiler = BzrProfiler()
            _profilers.profiler.start()
    if config.profiling.memory_profile_log:
        _profilers.memory_profile_start = (memory(), resident())

template = PageTemplateFile(
    os.path.join(os.path.dirname(__file__), 'profile.pt'))


@adapter(IEndRequestEvent)
def end_request(event):
    """If profiling is turned on, save profile data for the request."""
    if not config.profiling.profiling_allowed:
        return
    try:
        actions = _profilers.actions
    except AttributeError:
        # Some tests don't go through all the proper motions, like firing off
        # a start request event.  Just be quiet about it.
        return
    del _profilers.actions
    request = event.request
    # Create a timestamp including milliseconds.
    now = datetime.fromtimestamp(da.get_request_start_time())
    timestamp = "%s.%d" % (
        now.strftime('%Y-%m-%d_%H:%M:%S'), int(now.microsecond/1000.0))
    pageid = request._orig_env.get('launchpad.pageid', 'Unknown')
    oopsid = getattr(request, 'oopsid', None)
    content_type = request.response.getHeader('content-type')
    if content_type is None:
        content_type_params = {}
        is_html = False
    else:
        _major, _minor, content_type_params = parse(content_type)
        is_html = _major == 'text' and _minor == 'html'
    template_context = {
        'actions': actions,
        'always_log': config.profiling.profile_all_requests}
    if _profilers.profiler is not None:
        prof_stats = _profilers.profiler.stop()
        # Free some memory.
        del _profilers.profiler
        if oopsid is None:
            # Log an OOPS to get a log of the SQL queries, and other
            # useful information,  together with the profiling
            # information.
            info = (ProfilingOops, None, None)
            error_utility = getUtility(IErrorReportingUtility)
            oops = error_utility.handling(info, request)
            oopsid = oops.id
        else:
            oops = request.oops
        if 'log' in actions:
            filename = '%s-%s-%s-%s.prof' % (
                timestamp, pageid, oopsid,
                threading.currentThread().getName())
            dump_path = os.path.join(config.profiling.profile_dir, filename)
            prof_stats.save(dump_path, format="callgrind")
            template_context['dump_path'] = os.path.abspath(dump_path)
        if is_html and 'show' in actions:
            # Generate raw OOPS results.
            f = StringIO.StringIO()
            oops.write(f)
            template_context['oops'] = f.getvalue()
            # Generate profile summaries.
            for name in ('inlinetime', 'totaltime', 'callcount'):
                prof_stats.sort(name)
                f = StringIO.StringIO()
                prof_stats.pprint(top=25, file=f)
                template_context[name] = f.getvalue()
    if actions and is_html:
        # Hack the new HTML in at the end of the page.
        encoding = content_type_params.get('charset', 'utf-8')
        added_html = template.render(**template_context).encode(encoding)
        existing_html = request.response.consumeBody()
        e_start, e_close_body, e_end = existing_html.rpartition(
            '</body>')
        new_html = ''.join(
            (e_start, added_html, e_close_body, e_end))
        request.response.setResult(new_html)
    # Dump memory profiling info.
    if config.profiling.memory_profile_log:
        log = file(config.profiling.memory_profile_log, 'a')
        vss_start, rss_start = _profilers.memory_profile_start
        del _profilers.memory_profile_start
        vss_end, rss_end = memory(), resident()
        if oopsid is None:
            oopsid = '-'
        log.write('%s %s %s %f %d %d %d %d\n' % (
            timestamp, pageid, oopsid, da.get_request_duration(),
            vss_start, rss_start, vss_end, rss_end))
        log.close()


def get_desired_profile_actions(request):
    """What does the URL show that the user wants to do about profiling?

    Returns a set of actions (comma-separated) if ++profile++ is in the
    URL.  Note that ++profile++ alone without actions is interpreted as
    the "help" action.
    """
    result = set()
    path_info = request.get('PATH_INFO')
    if path_info:
        # if not, this is almost certainly a test not bothering to set up
        # certain bits.  We'll handle it silently.
        start, match, end = path_info.partition('/++profile++')
        # We don't need no steenkin' regex.
        if match:
            # Now we figure out what actions are desired.  Normally,
            # parsing the url segment after the namespace ('++profile++'
            # in this case) is done in the traverse method of the
            # namespace view (see ProfileNamespace in this file).  We
            # are doing it separately because we want to know what to do
            # before the traversal machinery gets started, so we can
            # include traversal in the profile.
            actions, slash, tail = end.partition('/')
            result.update(
                action for action in (
                    item.strip().lower() for item in actions.split(','))
                if action)
            result.intersection_update(('log', 'show'))
            if not result:
                result.add('help')
    return result


class ProfileNamespace(view):
    """A see-through namespace that handles traversals with ++profile++."""

    def traverse(self, name, remaining):
        """Continue on with traversal.
        """
        # Note that handling the name is done in get_desired_profile_actions,
        # above.  See the comment in that function.
        return self.context
