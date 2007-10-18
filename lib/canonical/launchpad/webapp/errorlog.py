# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Error logging facilities."""

__metaclass__ = type

import threading
import os
import errno
import re
import datetime
import pytz
import rfc822
import logging
import urllib

from zope.interface import implements

from zope.app.error.interfaces import IErrorReportingUtility
from zope.exceptions.exceptionformatter import format_exception

from canonical.config import config
from canonical.launchpad import versioninfo
from canonical.launchpad.webapp.adapter import (
    RequestExpired, get_request_statements, get_request_duration,
    soft_timeout_expired)
from canonical.launchpad.webapp.interfaces import (
    IErrorReport, IErrorReportRequest)
from canonical.launchpad.webapp.opstats import OpStats

UTC = pytz.utc

# the section of the OOPS ID before the instance identifier is the
# days since the epoch, which is defined as the start of 2006.
epoch = datetime.datetime(2006, 01, 01, 00, 00, 00, tzinfo=UTC)

# Restrict the rate at which errors are sent to the Zope event Log
# (this does not affect generation of error reports).
_rate_restrict_pool = {}

# The number of seconds that must elapse on average between sending two
# exceptions of the same name into the the Event Log. one per minute.
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
    try:
        value = str(obj)
    except:
        logging.getLogger('SiteError').exception(
            'Error in ErrorReportingService while getting a str '
            'representation of an object')
        value = '<unprintable %s object>' % (
            str(type(obj).__name__)
            )
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

    # Block HTTP_COOKIE
    if name == 'HTTP_COOKIE':
        return True

    # Allow remaining UPPERCASE names and remaining form variables.  Note that
    # XMLRPC requests won't have a form attribute.
    form = getattr(request, 'form', [])
    if name == upper_name or name in form:
        return False

    # Block everything else
    return True


class ErrorReport:
    implements(IErrorReport)

    def __init__(self, id, type, value, time, tb_text, username,
                 url, duration, req_vars, db_statements):
        self.id = id
        self.type = type
        self.value = value
        self.time = time
        self.tb_text = tb_text
        self.username = username
        self.url = url
        self.duration = duration
        self.req_vars = req_vars
        self.db_statements = db_statements
        self.branch_nick = versioninfo.branch_nick
        self.revno  = versioninfo.revno

    def __repr__(self):
        return '<ErrorReport %s>' % self.id

    def write(self, fp):
        fp.write('Oops-Id: %s\n' % _normalise_whitespace(self.id))
        fp.write('Exception-Type: %s\n' % _normalise_whitespace(self.type))
        fp.write('Exception-Value: %s\n' % _normalise_whitespace(self.value))
        fp.write('Date: %s\n' % self.time.isoformat())
        fp.write('Branch: %s\n' % self.branch_nick)
        fp.write('Revision: %s\n' % self.revno)
        fp.write('User: %s\n' % _normalise_whitespace(self.username))
        fp.write('URL: %s\n' % _normalise_whitespace(self.url))
        fp.write('Duration: %s\n' % self.duration)
        fp.write('\n')
        safe_chars = ';/\\?:@&+$, ()*!'
        for key, value in self.req_vars:
            fp.write('%s=%s\n' % (urllib.quote(key, safe_chars),
                                  urllib.quote(value, safe_chars)))
        fp.write('\n')
        for (start, end, statement) in self.db_statements:
            fp.write('%05d-%05d %s\n' % (start, end,
                                         _normalise_whitespace(statement)))
        fp.write('\n')
        fp.write(self.tb_text)

    @classmethod
    def read(cls, fp):
        msg = rfc822.Message(fp)
        id = msg.getheader('oops-id')
        exc_type = msg.getheader('exception-type')
        exc_value = msg.getheader('exception-value')
        date = msg.getheader('date')
        username = msg.getheader('user')
        url = msg.getheader('url')
        duration = int(msg.getheader('duration', '-1'))

        req_vars = []
        lines = msg.fp.readlines()
        for linenum, line in enumerate(lines):
            line = line.strip()
            if not line:
                break
            key, value = line.split('=', 1)
            req_vars.append((urllib.unquote(key), urllib.unquote(value)))

        statements = []
        lines = lines[linenum+1:]
        for linenum, line in enumerate(lines):
            line = line.strip()
            if not line:
                break
            startend, statement = line.split(' ', 1)
            start, end = startend.split('-')
            statements.append((int(start), int(end), statement))

        tb_text = ''.join(lines[linenum+1:])

        return cls(id, exc_type, exc_value, date, tb_text,
                   username, url, duration, req_vars, statements)


class ErrorReportingUtility:
    implements(IErrorReportingUtility)

    _ignored_exceptions = set(['Unauthorized', 'TranslationUnavailable'])
    copy_to_zlog = False

    lasterrordate = None
    lastid = 0

    def __init__(self):
        self.copy_to_zlog = config.launchpad.errorreports.copy_to_zlog
        self.lastid_lock = threading.Lock()

    def _findLastOopsId(self, directory):
        """Find the last error number used by this Launchpad instance

        The purpose of this function is to not repeat sequence numbers
        if the Launchpad instance is restarted.

        This method is not thread safe, and only intended to be called
        from the constructor.
        """
        prefix = config.launchpad.errorreports.oops_prefix
        lastid = 0
        for filename in os.listdir(directory):
            oopsid = filename.rsplit('.', 1)[1]
            if not oopsid.startswith(prefix):
                continue
            oopsid = oopsid[len(prefix):]
            if oopsid.isdigit() and int(oopsid) > lastid:
                lastid = int(oopsid)
        return lastid

    def errordir(self, now=None):
        """Find the directory to write error reports to.

        Error reports are written to subdirectories containing the
        date of the error.
        """
        if now is not None:
            now = now.astimezone(UTC)
        else:
            now = datetime.datetime.now(UTC)
        date = now.strftime('%Y-%m-%d')
        errordir = os.path.join(config.launchpad.errorreports.errordir, date)
        if date != self.lasterrordate:
            self.lastid_lock.acquire()
            try:
                self.lasterrordate = date
                # make sure the directory exists
                try:
                    os.makedirs(errordir)
                except OSError, e:
                    if e.errno != errno.EEXIST:
                        raise
                self.lastid = self._findLastOopsId(errordir)
            finally:
                self.lastid_lock.release()
        return errordir

    def newOopsId(self, now=None):
        """Returns an (oopsid, filename) pair for the next Oops ID

        The Oops ID is composed of a short string to identify the
        Launchpad instance followed by an ID that is unique for the
        day.

        The filename is composed of the zero padded second in the day
        followed by the Oops ID.  This ensures that error reports are
        in date order when sorted lexically.
        """
        if now is not None:
            now = now.astimezone(UTC)
        else:
            now = datetime.datetime.now(UTC)
        # we look up the error directory before allocating a new ID,
        # because if the day has changed, errordir() will reset the ID
        # counter to zero
        errordir = self.errordir(now)
        self.lastid_lock.acquire()
        try:
            self.lastid += 1
            newid = self.lastid
        finally:
            self.lastid_lock.release()
        day_number = (now - epoch).days + 1
        second_in_day = now.hour * 3600 + now.minute * 60 + now.second
        oops_prefix = config.launchpad.errorreports.oops_prefix
        oops = 'OOPS-%d%s%d' % (day_number, oops_prefix, newid)
        filename = os.path.join(errordir, '%05d.%s%s' % (second_in_day,
                                                         oops_prefix,
                                                         newid))
        return oops, filename

    def raising(self, info, request=None, now=None):
        """See IErrorReportingUtility.raising()"""
        if now is not None:
            now = now.astimezone(UTC)
        else:
            now = datetime.datetime.now(UTC)
        try:
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

            if request:
                # XXX jamesh 2005-11-22: Temporary fix, which Steve should
                #      undo. URL is just too HTTPRequest-specific.
                if hasattr(request, 'URL'):
                    url = request.URL
                try:
                    # XXX jamesh 2005-11-22: UnauthenticatedPrincipal
                    # does not have getLogin()
                    if hasattr(request.principal, 'getLogin'):
                        login = request.principal.getLogin()
                    else:
                        login = 'unauthenticated'
                    username = _safestr(
                        ', '.join(map(unicode, (login,
                                                request.principal.id,
                                                request.principal.title,
                                                request.principal.description
                                                ))))
                # XXX jamesh 2005-11-22:
                # When there's an unauthorized access, request.principal is
                # not set, so we get an AttributeError.
                # Is this right? Surely request.principal should be set!
                # Answer: Catching AttributeError is correct for the
                #         simple reason that UnauthenticatedUser (which
                #         I always use during coding), has no 'getLogin()'
                #         method. However, for some reason this except
                #         does **NOT** catch these errors.
                except AttributeError:
                    pass

                req_vars = []
                for key, value in request.items():
                    if _is_sensitive(request, key):
                        req_vars.append((_safestr(key), '<hidden>'))
                    else:
                        req_vars.append((_safestr(key), _safestr(value)))
                req_vars.sort()
            strv = _safestr(info[1])

            strurl = _safestr(url)

            duration = get_request_duration()

            statements = sorted((start, end, _safestr(statement))
                                for (start, end, statement)
                                    in get_request_statements())

            oopsid, filename = self.newOopsId(now)

            entry = ErrorReport(oopsid, strtype, strv, now, tb_text,
                                username, strurl, duration,
                                req_vars, statements)
            entry.write(open(filename, 'wb'))

            if request:
                request.oopsid = oopsid

            if self.copy_to_zlog:
                self._do_copy_to_zlog(now, strtype, strurl, info, oopsid)
        finally:
            info = None

    def _do_copy_to_zlog(self, now, strtype, url, info, oopsid):
        distant_past = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=UTC)
        when = _rate_restrict_pool.get(strtype, distant_past)
        if now > when:
            next_when = max(when,
                            now - _rate_restrict_burst*_rate_restrict_period)
            next_when += _rate_restrict_period
            _rate_restrict_pool[strtype] = next_when
            # The logging module doesn't provide a way to pass in
            # exception info, so we temporarily raise the exception so
            # it can be logged.
            try:
                raise info[0], info[1], info[2]
            except:
                logging.getLogger('SiteError').exception(
                    '%s (%s)' % (url, oopsid))


globalErrorUtility = ErrorReportingUtility()


class ErrorReportRequest:
    implements(IErrorReportRequest)

    oopsid = None


class ScriptRequest(ErrorReportRequest):
    """Fake request that can be passed to ErrorReportingUtility.raising.

    It can be used by scripts to enrich error reports with context information
    and a representation of the resource on which the error occured. It also
    gives access to the generated OOPS id.

    The resource for which the error occured MAY be identified by an URL. This
    URL should point to a human-readable representation of the model object,
    such as a page on launchpad.net, even if this URL does not occur as part of
    the normal operation of the script.

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


class SoftRequestTimeout(RequestExpired):
    """Soft request timeout expired"""


def end_request(event):
    # if no OOPS has been generated at the end of the request, but
    # the soft timeout has expired, log an OOPS.
    if event.request.oopsid is None and soft_timeout_expired():
        OpStats.stats['soft timeouts'] += 1
        globalErrorUtility.raising(
            (SoftRequestTimeout, SoftRequestTimeout(event.object), None),
            event.request)

