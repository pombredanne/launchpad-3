# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0702

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
import types
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
    # We disable the pylint warning for the blank except.
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

    def __init__(self, id, type, value, time, pageid, tb_text, username,
                 url, duration, req_vars, db_statements):
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
        self.revno  = versioninfo.revno

    def __repr__(self):
        return '<ErrorReport %s>' % self.id

    def write(self, fp):
        fp.write('Oops-Id: %s\n' % _normalise_whitespace(self.id))
        fp.write('Exception-Type: %s\n' % _normalise_whitespace(self.type))
        fp.write('Exception-Value: %s\n' % _normalise_whitespace(self.value))
        fp.write('Date: %s\n' % self.time.isoformat())
        fp.write('Page-Id: %s\n' % _normalise_whitespace(self.pageid))
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
        pageid = msg.getheader('page-id')
        username = msg.getheader('user')
        url = msg.getheader('url')
        duration = int(msg.getheader('duration', '-1'))

        # Explicitely use an iterator so we can process the file
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
            startend, statement = line.split(' ', 1)
            start, end = startend.split('-')
            statements.append((int(start), int(end), statement))

        # The rest is traceback.
        tb_text = ''.join(lines)

        return cls(id, exc_type, exc_value, date, pageid, tb_text,
                   username, url, duration, req_vars, statements)


class ErrorReportingUtility:
    implements(IErrorReportingUtility)

    _ignored_exceptions = set(['Unauthorized', 'TranslationUnavailable'])

    lasterrordir = None
    lastid = 0

    def __init__(self):
        self.lastid_lock = threading.Lock()
        self.prefix = config.error_reports.oops_prefix

    def setOopsToken(self, token):
        """Append a string to the oops prefix.

        :param token: a string to append to a oops_prefix.
            Scripts that run multiple processes can append a string to
            the oops_prefix to create a unique identifier for each
            process.
        """
        self.prefix = config.error_reports.oops_prefix + token

    def _findLastOopsIdFilename(self, directory):
        """Find details of the last OOPS reported in the given directory.

        This function only considers OOPSes with the currently
        configured oops_prefix.

        :return: a tuple (oops_id, oops_filename), which will be (0,
            None) if no OOPS is found.
        """
        prefix = self.prefix
        lastid = 0
        lastfilename = None
        for filename in os.listdir(directory):
            oopsid = filename.rsplit('.', 1)[1]
            if not oopsid.startswith(prefix):
                continue
            oopsid = oopsid[len(prefix):]
            if oopsid.isdigit() and int(oopsid) > lastid:
                lastid = int(oopsid)
                lastfilename = filename
        return lastid, lastfilename

    def _findLastOopsId(self, directory):
        """Find the last error number used by this Launchpad instance.

        The purpose of this function is to not repeat sequence numbers
        if the Launchpad instance is restarted.

        This method is not thread safe, and only intended to be called
        from the constructor.
        """
        return self._findLastOopsIdFilename(directory)[0]

    def getOopsReport(self, time):
        """Return the contents of the OOPS report logged at 'time'."""
        oops_filename = self.getOopsFilename(
            self._findLastOopsId(self.errordir(time)), time)
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
        directory = self.errordir(now)
        oopsid, filename = self._findLastOopsIdFilename(directory)
        if filename is None:
            directory = self.errordir(now - datetime.timedelta(days=1))
            oopsid, filename = self._findLastOopsIdFilename(directory)
            if filename is None:
                return None
        oops_report = open(os.path.join(directory, filename), 'r')
        try:
            return ErrorReport.read(oops_report)
        finally:
            oops_report.close()

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
        errordir = os.path.join(config.error_reports.errordir, date)
        if errordir != self.lasterrordir:
            self.lastid_lock.acquire()
            try:
                self.lasterrordir = errordir
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

    def getOopsFilename(self, oops_id, time):
        """Get the filename for a given OOPS id and time."""
        oops_prefix = self.prefix
        error_dir = self.errordir(time)
        second_in_day = time.hour * 3600 + time.minute * 60 + time.second
        return os.path.join(
            error_dir, '%05d.%s%s' % (second_in_day, oops_prefix, oops_id))

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
        oops_prefix = self.prefix
        day_number = (now - epoch).days + 1
        oops = 'OOPS-%d%s%d' % (day_number, oops_prefix, newid)
        filename = self.getOopsFilename(newid, now)
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
            pageid = ''

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
                        ', '.join([
                                unicode(login),
                                unicode(request.principal.id),
                                unicode(request.principal.title),
                                unicode(request.principal.description)]))
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

                if getattr(request, '_orig_env', None):
                    pageid = request._orig_env.get('launchpad.pageid', '')

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

            entry = ErrorReport(oopsid, strtype, strv, now, pageid, tb_text,
                                username, strurl, duration,
                                req_vars, statements)
            entry.write(open(filename, 'wb'))

            if request:
                request.oopsid = oopsid

            if config.error_reports.copy_to_zlog:
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

