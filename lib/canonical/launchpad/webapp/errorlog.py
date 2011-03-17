# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0702

"""Error logging facilities."""

__metaclass__ = type

import contextlib
import datetime
from itertools import repeat
import logging
import os
import stat
import re
import rfc822
import types
import urllib

from lazr.restful.utils import get_current_browser_request
import pytz
from zope.component.interfaces import ObjectEvent
from zope.error.interfaces import IErrorReportingUtility
from zope.event import notify
from zope.exceptions.exceptionformatter import format_exception
from zope.interface import implements
from zope.publisher.interfaces.xmlrpc import IXMLRPCRequest
from zope.traversing.namespace import view

from canonical.config import config
from lp.app import versioninfo
from canonical.launchpad.layers import WebServiceLayer
from canonical.launchpad.webapp.adapter import (
    get_request_duration,
    soft_timeout_expired,
    )
from canonical.launchpad.webapp.interfaces import (
    IErrorReport,
    IErrorReportEvent,
    IErrorReportRequest,
    )
from canonical.launchpad.webapp.opstats import OpStats
from canonical.lazr.utils import safe_hasattr
from lp.services.log.uniquefileallocator import UniqueFileAllocator
from lp.services.timeline.requesttimeline import get_request_timeline

UTC = pytz.utc

LAZR_OOPS_USER_REQUESTED_KEY = 'lazr.oops.user_requested'

# Restrict the rate at which errors are sent to the Zope event Log
# (this does not affect generation of error reports).
_rate_restrict_pool = {}

# The number of seconds that must elapse on average between sending two
# exceptions of the same name into the Event Log. one per minute.
_rate_restrict_period = datetime.timedelta(seconds=60)

# The number of exceptions to allow in a burst before the above limit
# kicks in. We allow five exceptions, before limiting them to one per
# minute.
_rate_restrict_burst = 5


def _normalise_whitespace(s):
    """Normalise the whitespace in a string to spaces"""
    if s is None:
        return None
    return ' '.join(s.split())


def _safestr(obj):
    if isinstance(obj, unicode):
        return obj.replace('\\', '\\\\').encode('ASCII',
                                                'backslashreplace')
    # A call to str(obj) could raise anything at all.
    # We'll ignore these errors, and print something
    # useful instead, but also log the error.
    # We disable the pylint warning for the blank except.
    try:
        value = str(obj)
    except:
        logging.getLogger('SiteError').exception(
            'Error in ErrorReportingService while getting a str '
            'representation of an object')
        value = '<unprintable %s object>' % (
            str(type(obj).__name__))
    # Some str() calls return unicode objects.
    if isinstance(value, unicode):
        return _safestr(value)
    # encode non-ASCII characters
    value = value.replace('\\', '\\\\')
    value = re.sub(r'[\x80-\xff]',
                   lambda match: '\\x%02x' % ord(match.group(0)), value)
    return value


def _is_sensitive(request, name):
    """Return True if the given request variable name is sensitive.

    Sensitive request variables should not be recorded in OOPS
    reports.  Currently we consider the following to be sensitive:
     * any name containing 'password' or 'passwd'
     * cookies
     * the HTTP_COOKIE header.
    """
    upper_name = name.upper()
    # Block passwords
    if ('PASSWORD' in upper_name or 'PASSWD' in upper_name):
        return True

    # Block HTTP_COOKIE and oauth_signature.
    if name in ('HTTP_COOKIE', 'oauth_signature'):
        return True

    # Allow remaining UPPERCASE names and remaining form variables.  Note that
    # XMLRPC requests won't have a form attribute.
    form = getattr(request, 'form', [])
    if name == upper_name or name in form:
        return False

    # Block everything else
    return True


def parse_iso8601_date(datestring):
    """Parses a standard ISO 8601 format date, ignoring time zones.

    Performs no validation whatsoever. It just plucks up to the first
    7 numbers from the string and passes them to `datetime.datetime`,
    so would in fact parse any string containing reasonable numbers.

    This function can be replaced with `datetime.datetime.strptime()`
    once we move to Python 2.5.
    """
    return datetime.datetime(
        *(int(elem) for elem in re.findall('[0-9]+', datestring)[:7]))


class ErrorReportEvent(ObjectEvent):
    """A new error report has been created."""
    implements(IErrorReportEvent)


class ErrorReport:
    implements(IErrorReport)

    def __init__(self, id, type, value, time, pageid, tb_text, username,
                 url, duration, req_vars, db_statements, informational):
        self.id = id
        self.type = type
        self.value = value
        self.time = time
        self.pageid = pageid
        self.tb_text = tb_text
        self.username = username
        self.url = url
        self.duration = duration
        self.req_vars = req_vars
        self.db_statements = db_statements
        self.branch_nick = versioninfo.branch_nick
        self.revno = versioninfo.revno
        self.informational = informational

    def __repr__(self):
        return '<ErrorReport %s %s: %s>' % (self.id, self.type, self.value)

    def get_chunks(self):
        """Returns a list of bytestrings making up the oops disk content."""
        chunks = []
        chunks.append('Oops-Id: %s\n' % _normalise_whitespace(self.id))
        chunks.append(
            'Exception-Type: %s\n' % _normalise_whitespace(self.type))
        chunks.append(
            'Exception-Value: %s\n' % _normalise_whitespace(self.value))
        chunks.append('Date: %s\n' % self.time.isoformat())
        chunks.append('Page-Id: %s\n' % _normalise_whitespace(self.pageid))
        chunks.append('Branch: %s\n' % _safestr(self.branch_nick))
        chunks.append('Revision: %s\n' % self.revno)
        chunks.append('User: %s\n' % _normalise_whitespace(self.username))
        chunks.append('URL: %s\n' % _normalise_whitespace(self.url))
        chunks.append('Duration: %s\n' % self.duration)
        chunks.append('Informational: %s\n' % self.informational)
        chunks.append('\n')
        safe_chars = ';/\\?:@&+$, ()*!'
        for key, value in self.req_vars:
            chunks.append('%s=%s\n' % (urllib.quote(key, safe_chars),
                                  urllib.quote(value, safe_chars)))
        chunks.append('\n')
        for (start, end, database_id, statement) in self.db_statements:
            chunks.append('%05d-%05d@%s %s\n' % (
                start, end, database_id, _normalise_whitespace(statement)))
        chunks.append('\n')
        chunks.append(self.tb_text)
        return chunks

    def write(self, fp):
        fp.writelines(self.get_chunks())

    @classmethod
    def read(cls, fp):
        msg = rfc822.Message(fp)
        id = msg.getheader('oops-id')
        exc_type = msg.getheader('exception-type')
        exc_value = msg.getheader('exception-value')
        date = parse_iso8601_date(msg.getheader('date'))
        pageid = msg.getheader('page-id')
        username = msg.getheader('user')
        url = msg.getheader('url')
        duration = int(float(msg.getheader('duration', '-1')))
        informational = msg.getheader('informational')

        # Explicitly use an iterator so we can process the file
        # sequentially. In most instances the iterator will actually
        # be the file object passed in because file objects should
        # support iteration.
        lines = iter(msg.fp)

        # Request variables until the first blank line.
        req_vars = []
        for line in lines:
            line = line.strip()
            if line == '':
                break
            key, value = line.split('=', 1)
            req_vars.append((urllib.unquote(key), urllib.unquote(value)))

        # Statements until the next blank line.
        statements = []
        for line in lines:
            line = line.strip()
            if line == '':
                break
            match = re.match(
                r'^(\d+)-(\d+)(?:@([\w-]+))?\s+(.*)', line)
            assert match is not None, (
                "Unable to interpret oops line: %s" % line)
            start, end, db_id, statement = match.groups()
            if db_id is not None:
                db_id = intern(db_id) # This string is repeated lots.
            statements.append(
                (int(start), int(end), db_id, statement))

        # The rest is traceback.
        tb_text = ''.join(lines)

        return cls(id, exc_type, exc_value, date, pageid, tb_text,
                   username, url, duration, req_vars, statements,
                   informational)


class ErrorReportingUtility:
    implements(IErrorReportingUtility)

    _ignored_exceptions = set([
        'ReadOnlyModeDisallowedStore', 'ReadOnlyModeViolation',
        'TranslationUnavailable', 'NoReferrerError'])
    _ignored_exceptions_for_unauthenticated_users = set(['Unauthorized'])
    _default_config_section = 'error_reports'

    def __init__(self):
        self.configure()
        self._oops_messages = {}
        self._oops_message_key_iter = (
            index for index, _ignored in enumerate(repeat(None)))

    def configure(self, section_name=None):
        """Configure the utility using the named section from the config.

        The 'error_reports' section is used if section_name is None.
        """
        if section_name is None:
            section_name = self._default_config_section
        self.copy_to_zlog = config[section_name].copy_to_zlog
        # Start a new UniqueFileAllocator to activate the new configuration.
        self.log_namer = UniqueFileAllocator(
            output_root=config[section_name].error_dir,
            log_type="OOPS",
            log_subtype=config[section_name].oops_prefix,
            )

    def setOopsToken(self, token):
        return self.log_namer.setToken(token)

    @property
    def oops_prefix(self):
        """Get the current effective oops prefix.

        This is the log subtype + anything set via setOopsToken.
        """
        return self.log_namer.get_log_infix()

    def getOopsReport(self, time):
        """Return the contents of the OOPS report logged at 'time'."""
        # How this works - get a serial that was logging in the dir
        # that logs for time are logged in.
        serial_from_time = self.log_namer._findHighestSerial(
            self.log_namer.output_dir(time))
        # Calculate a filename which combines this most recent serial,
        # the current log_namer naming rules and the exact timestamp.
        oops_filename = self.log_namer.getFilename(serial_from_time, time)
        # Note that if there were no logs written, or if there were two
        # oops that matched the time window of directory on disk, this
        # call can raise an IOError.
        oops_report = open(oops_filename, 'r')
        try:
            return ErrorReport.read(oops_report)
        finally:
            oops_report.close()

    def getLastOopsReport(self):
        """Return the last ErrorReport reported with the current config.

        This should only be used in integration tests.

        Note that this function only checks for OOPSes reported today
        and yesterday (to avoid midnight bugs where an OOPS is logged
        at 23:59:59 but not checked for until 0:00:01), and ignores
        OOPSes recorded longer ago.

        Returns None if no OOPS is found.
        """
        now = datetime.datetime.now(UTC)
        # Check today
        oopsid, filename = self.log_namer._findHighestSerialFilename(time=now)
        if filename is None:
            # Check yesterday, we may have just passed midnight.
            yesterday = now - datetime.timedelta(days=1)
            oopsid, filename = self.log_namer._findHighestSerialFilename(
                time=yesterday)
            if filename is None:
                return None
        oops_report = open(filename, 'r')
        try:
            return ErrorReport.read(oops_report)
        finally:
            oops_report.close()

    def raising(self, info, request=None, now=None):
        """See IErrorReportingUtility.raising()

        :param now: The datetime to use as the current time.  Will be
            determined if not supplied.  Useful for testing.  Not part of
            IErrorReportingUtility).
        """
        return self._raising(
            info, request=request, now=now, informational=False)

    def _raising(self, info, request=None, now=None, informational=False):
        """Private method used by raising() and handling()."""
        entry = self._makeErrorReport(info, request, now, informational)
        if entry is None:
            return
        filename = entry._filename
        entry.write(open(filename, 'wb'))
        # Set file permission to: rw-r--r--
        wanted_permission = (
            stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        os.chmod(filename, wanted_permission)
        if request:
            request.oopsid = entry.id
            request.oops = entry

        if self.copy_to_zlog:
            self._do_copy_to_zlog(
                entry.time, entry.type, entry.url, info, entry.id)
        notify(ErrorReportEvent(entry))
        return entry

    def _makeErrorReport(self, info, request=None, now=None,
                         informational=False):
        """Return an ErrorReport for the supplied data.

        :param info: Output of sys.exc_info()
        :param request: The IErrorReportRequest which provides context to the
            info.
        :param now: The datetime to use as the current time.  Will be
            determined if not supplied.  Useful for testing.
        :param informational: If true, the report is flagged as informational
            only.
        """
        if now is not None:
            now = now.astimezone(UTC)
        else:
            now = datetime.datetime.now(UTC)
        tb_text = None

        strtype = str(getattr(info[0], '__name__', info[0]))
        if strtype in self._ignored_exceptions:
            return

        if not isinstance(info[2], basestring):
            tb_text = ''.join(format_exception(*info,
                                               **{'as_html': False}))
        else:
            tb_text = info[2]
        tb_text = _safestr(tb_text)

        url = None
        username = None
        req_vars = []
        pageid = ''

        if request:
            # XXX jamesh 2005-11-22: Temporary fix, which Steve should
            #      undo. URL is just too HTTPRequest-specific.
            if safe_hasattr(request, 'URL'):
                url = request.URL

            if WebServiceLayer.providedBy(request):
                webservice_error = getattr(
                    info[0], '__lazr_webservice_error__', 500)
                if webservice_error / 100 != 5:
                    request.oopsid = None
                    # Return so the OOPS is not generated.
                    return

            missing = object()
            principal = getattr(request, 'principal', missing)
            if safe_hasattr(principal, 'getLogin'):
                login = principal.getLogin()
            elif principal is missing or principal is None:
                # Request has no principal.
                login = None
            else:
                # Request has an UnauthenticatedPrincipal.
                login = 'unauthenticated'
                if strtype in (
                    self._ignored_exceptions_for_unauthenticated_users):
                    return

            if principal is not None and principal is not missing:
                username = _safestr(
                    ', '.join([
                            unicode(login),
                            unicode(request.principal.id),
                            unicode(request.principal.title),
                            unicode(request.principal.description)]))

            if getattr(request, '_orig_env', None):
                pageid = request._orig_env.get('launchpad.pageid', '')

            for key, value in request.items():
                if _is_sensitive(request, key):
                    req_vars.append((_safestr(key), '<hidden>'))
                else:
                    req_vars.append((_safestr(key), _safestr(value)))
            if IXMLRPCRequest.providedBy(request):
                args = request.getPositionalArguments()
                req_vars.append(('xmlrpc args', _safestr(args)))
        # XXX AaronBentley 2009-11-26 bug=488950: There should be separate
        # storage for oops messages.
        req_vars.extend(
            ('<oops-message-%d>' % key, str(message)) for key, message
             in self._oops_messages.iteritems())
        req_vars.sort()
        strv = _safestr(info[1])

        strurl = _safestr(url)

        duration = get_request_duration()
        # In principle the timeline is per-request, but see bug=623199 -
        # at this point the request is optional, but get_request_timeline
        # does not care; when it starts caring, we will always have a
        # request object (or some annotations containing object).
        # RBC 20100901
        timeline = get_request_timeline(request)
        statements = []
        for action in timeline.actions:
            start, end, category, detail = action.logTuple()
            statements.append(
                (start, end, _safestr(category), _safestr(detail)))

        oopsid, filename = self.log_namer.newId(now)

        result = ErrorReport(oopsid, strtype, strv, now, pageid, tb_text,
                           username, strurl, duration,
                           req_vars, statements,
                           informational)
        result._filename = filename
        return result

    def handling(self, info, request=None, now=None):
        """Flag ErrorReport as informational only.

        :param info: Output of sys.exc_info()
        :param request: The IErrorReportRequest which provides context to the
            info.
        :param now: The datetime to use as the current time.  Will be
            determined if not supplied.  Useful for testing.
        :return: The ErrorReport created.
        """
        return self._raising(
            info, request=request, now=now, informational=True)

    def _do_copy_to_zlog(self, now, strtype, url, info, oopsid):
        distant_past = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=UTC)
        when = _rate_restrict_pool.get(strtype, distant_past)
        if now > when:
            next_when = max(when,
                            now - _rate_restrict_burst*_rate_restrict_period)
            next_when += _rate_restrict_period
            _rate_restrict_pool[strtype] = next_when
            # Sometimes traceback information can be passed in as a string. In
            # those cases, we don't (can't!) log the traceback. The traceback
            # information is still preserved in the actual OOPS report.
            traceback = info[2]
            if not isinstance(traceback, types.TracebackType):
                traceback = None
            # The logging module doesn't provide a way to pass in exception
            # info, so we temporarily raise the exception so it can be logged.
            # We disable the pylint warning for the blank except.
            try:
                raise info[0], info[1], traceback
            except info[0]:
                logging.getLogger('SiteError').exception(
                    '%s (%s)' % (url, oopsid))

    @contextlib.contextmanager
    def oopsMessage(self, message):
        """Add an oops message to be included in oopses from this context."""
        key = self._oops_message_key_iter.next()
        self._oops_messages[key] = message
        try:
            yield
        finally:
            del self._oops_messages[key]


globalErrorUtility = ErrorReportingUtility()


class ErrorReportRequest:
    implements(IErrorReportRequest)

    oopsid = None


class ScriptRequest(ErrorReportRequest):
    """Fake request that can be passed to ErrorReportingUtility.raising.

    It can be used by scripts to enrich error reports with context information
    and a representation of the resource on which the error occurred. It also
    gives access to the generated OOPS id.

    The resource for which the error occurred MAY be identified by an URL.
    This URL should point to a human-readable representation of the model
    object, such as a page on launchpad.net, even if this URL does not occur
    as part of the normal operation of the script.

    :param data: context information relevant to diagnosing the error. It is
        recorded as request-variables in the OOPS.
    :type data: iterable of (key, value) tuples. Keys need not be unique.
    :param URL: initial value of the URL instance variable.

    :ivar URL: pointer to a representation of the resource for which the error
        occured. Defaults to None.
    :ivar oopsid: the oopsid set by ErrorReportingUtility.raising. Initially
        set to None.
    """

    def __init__(self, data, URL=None):
        self._data = list(data)
        self.oopsid = None
        self.URL = URL

    def items(self):
        return self._data

    @property
    def form(self):
        return dict(self.items())


class OopsLoggingHandler(logging.Handler):
    """Python logging handler that records OOPSes on exception."""

    def __init__(self, error_utility=None, request=None):
        """Construct an `OopsLoggingHandler`.

        :param error_utility: The error utility to use to log oopses. If not
            provided, defaults to `globalErrorUtility`.
        :param request: The `IErrorReportRequest` these errors are associated
            with.
        """
        logging.Handler.__init__(self, logging.ERROR)
        if error_utility is None:
            error_utility = globalErrorUtility
        self._error_utility = error_utility
        self._request = request

    def emit(self, record):
        """See `logging.Handler.emit`."""
        info = record.exc_info
        if info is not None:
            self._error_utility.raising(info, self._request)


class SoftRequestTimeout(Exception):
    """Soft request timeout expired"""


def end_request(event):
    # if no OOPS has been generated at the end of the request, but
    # the soft timeout has expired, log an OOPS.
    if event.request.oopsid is None and soft_timeout_expired():
        OpStats.stats['soft timeouts'] += 1
        globalErrorUtility.raising(
            (SoftRequestTimeout, SoftRequestTimeout(event.object), None),
            event.request)


class UserRequestOops(Exception):
    """A user requested OOPS to log statements."""


def maybe_record_user_requested_oops():
    """If an OOPS has been requested, report one.

    :return: The oopsid of the requested oops.  Returns None if an oops was
        not requested, or if there is already an OOPS.
    """
    request = get_current_browser_request()
    # If there is no request, or there is an oops already, then return.
    if (request is None or
        request.oopsid is not None or
        not request.annotations.get(LAZR_OOPS_USER_REQUESTED_KEY, False)):
        return None
    globalErrorUtility.handling(
        (UserRequestOops, UserRequestOops(), None), request)
    return request.oopsid


class OopsNamespace(view):
    """A namespace handle traversals with ++oops++."""

    def traverse(self, name, ignored):
        """Record that an oops has been requested and return the context."""
        # Store the oops request in the request annotations.
        self.request.annotations[LAZR_OOPS_USER_REQUESTED_KEY] = True
        return self.context
