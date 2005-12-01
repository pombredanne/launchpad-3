# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Error logging facilities."""

__metaclass__ = type

import threading
import os
import errno
import datetime
import pytz
import rfc822
import logging

from zope.interface import implements

from zope.app.errorservice.interfaces import (
    IErrorReportingService, ILocalErrorReportingService)
from zope.exceptions.exceptionformatter import format_exception

from zope.security.checker import ProxyFactory, NamesChecker
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.webapp.interfaces import (
    IErrorReport, IErrorReportRequest)

UTC = pytz.timezone('UTC')

#Restrict the rate at which errors are sent to the Event Log
_rate_restrict_pool = {}

# The number of seconds that must elapse on average between sending two
# exceptions of the same name into the the Event Log. one per minute.
_rate_restrict_period = datetime.timedelta(seconds=60)

# The number of exceptions to allow in a burst before the above limit
# kicks in. We allow five exceptions, before limiting them to one per
# minute.
_rate_restrict_burst = 5


class ErrorReport:
    implements(IErrorReport)

    def __init__(self, id, type, value, time, tb_text, username,
                 url, req_vars):
        self.id = id
        self.type = type
        self.value = value
        self.time = time
        self.tb_text = tb_text
        self.username = username
        self.url = url
        self.req_vars = req_vars

    @property
    def req_html(self):
        result = ['<table class="listing">',
                  '<thead><tr><th>Name</th><th>Value</th></tr></thead>'
                  '<tbody>']
        
        for key, value in self.req_vars:
            result.append('<tr><td>%s</td><td>%s</td></tr>' % (key, value))
        result.append('</tbody></table>')
        return '\n'.join(result)

    def __repr__(self):
        return '<ErrorReport %s>' % self.id

    def write(self, fp):
        fp.write('Oops-Id: %s\n' % self.id)
        fp.write('Exception-Type: %s\n' % self.type)
        fp.write('Exception-Value: %s\n' % self.value)
        fp.write('Date: %s\n' % self.time.isoformat())
        fp.write('User: %s\n' % self.username)
        fp.write('URL: %s\n\n' % self.url)
        for key, value in self.req_vars:
            fp.write('%s=%s\n' % (key, value))
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

        req_vars = []
        lines = msg.fp.readlines()
        for linenum, line in enumerate(lines):
            line = line.strip()
            if not line: break
            key, value = line.split('=', 1)
            req_vars.append((key, value))
        tb_text = ''.join(lines[linenum+1:])

        return cls(id, exc_type, exc_value, date, tb_text,
                   username, url, req_vars)

class ErrorReportingService:
    implements(IErrorReportingService, ILocalErrorReportingService)

    _ignored_exceptions = set(['Unauthorized'])
    copy_to_zlog = False

    lasterrordate = None
    lastid = 0

    def __init__(self):
        self.copy_to_zlog = config.launchpad.errorreports.copy_to_zlog
        self.lastid_lock = threading.Lock()
        self.lastid = self.findLastOopsId()

    def findLastOopsId(self):
        """Find the last error number used by this Launchpad instance

        The purpose of this function is to not repeat sequence numbers
        if the Launchpad instance is restarted.
        """
        prefix = config.launchpad.errorreports.oops_prefix
        lastid = 0
        for filename in os.listdir(self.errordir()):
            oopsid = filename.rsplit('.', 1)[1]
            if not oopsid.startswith(prefix):
                continue
            oopsid = oopsid[len(prefix):]
            if oopsid.isdigit() and int(oopsid) > lastid:
                lastid = int(oopsid)
        return lastid

    def errordir(self, now=None):
        if now is None:
            now = datetime.datetime.now(UTC)
        date = now.strftime('%Y-%m-%d')
        errordir = os.path.join(config.launchpad.errorreports.errordir, date)
        if date != self.lasterrordate:
            self.lastid_lock.acquire()
            try:
                self.lastid = 0
                self.lasterrordate = date
                # make sure the directory exists
                try:
                    os.makedirs(errordir)
                except OSError, e:
                    if e.errno != errno.EEXIST:
                        raise
            finally:
                self.lastid_lock.release()
        return errordir

    def newOopsId(self, now=None):
        """Returns an (oopsid, filename) pair for the next Oops ID"""
        if now is None:
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
        second_in_day = now.hour * 3600 + now.minute * 60 + now.second
        oops_prefix = config.launchpad.errorreports.oops_prefix
        oops = 'OOPS-%s%d' % (oops_prefix, newid)
        filename = os.path.join(errordir, '%05d.%s%s' % (second_in_day,
                                                         oops_prefix,
                                                         newid))
        return oops, filename

    def safestr(self, obj):
        if isinstance(obj, unicode):
            return obj.encode('ASCII', 'replace')

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
        return value

    def raising(self, info, request=None, now=None):
        """See IErrorReportingService.raising()"""
        if now is None:
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

            url = None
            username = None
            req_vars = []

            if request:
                # XXX: Temporary fix, which Steve should undo. URL is
                #      just too HTTPRequest-specific.
                if hasattr(request, 'URL'):
                    url = request.URL
                try:
                    # XXX: UnauthenticatedPrincipal does not have getLogin()
                    if hasattr(request.principal, 'getLogin'):
                        login = request.principal.getLogin()
                    else:
                        login = 'unauthenticated'
                    username = ', '.join(map(unicode, (login,
                                          request.principal.id,
                                          request.principal.title,
                                          request.principal.description
                                         ))).encode('ascii','replace')
                # When there's an unauthorized access, request.principal is
                # not set, so we get an AttributeError
                # XXX is this right? Surely request.principal should be set!
                # XXX Answer: Catching AttributeError is correct for the
                #             simple reason that UnauthenticatedUser (which
                #             I always use during coding), has no 'getLogin()'
                #             method. However, for some reason this except
                #             does **NOT** catch these errors.
                except AttributeError:
                    pass

                req_vars = sorted((key, self.safestr(value))
                                  for (key, value) in request.items())
            strv = self.safestr(info[1])

            strurl = self.safestr(url)

            oopsid, filename = self.newOopsId(now)

            entry = ErrorReport(oopsid, strtype, strv, now, tb_text,
                                username, strurl, req_vars)
            entry.write(open(filename, 'wb'))

            if request:
                request.setOopsId(oopsid)

            if self.copy_to_zlog:
                self._do_copy_to_zlog(now, strtype, strurl, info, oopsid)
        finally:
            info = None

    def _do_copy_to_zlog(self, now, strtype, url, info, oopsid):
        # XXX info is unused; logging.exception() will call sys.exc_info()
        # work around this with an evil hack
        distant_past = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=UTC)
        when = _rate_restrict_pool.get(strtype, distant_past)
        if now > when:
            next_when = max(when,
                            now - _rate_restrict_burst*_rate_restrict_period)
            next_when += _rate_restrict_period
            _rate_restrict_pool[strtype] = next_when
            try:
                raise info[0], info[1], info[2]
            except:
                logging.getLogger('SiteError').exception(
                    '%s (%s)' % (url, oopsid))

    def getProperties(self):
        """See ILocalErrorReportingService.getProperties()"""
        return {}

    def setProperties(self, keep_entries, copy_to_zlog=0,
                      ignored_exceptions=()):
        """See ILocalErrorReportingService.setProperties()"""
        raise NotImplementedError

    def getLogEntries(self):
        """See ILocalErrorReportingService.getLogEntries()"""
        errordir = self.errordir()
        files = os.listdir(errordir)
        # since the file names start with a zero padded "second in day",
        # lexical sorting leaves them in order of occurrence.
        files.sort()
        entries = []
        for filename in files[-50:]:
            filename = os.path.join(errordir, filename)
            entries.append(ErrorReport.read(open(filename, 'rb')))
        return entries

    def getLogEntryById(self, id):
        """See ILocalErrorReportingService.getLogEntryById"""
        if not id.startswith('OOPS-'):
            return None
        suffix = '.%s' % id[5:]
        errordir = self.errordir()
        files = os.listdir(errordir)
        for filename in files:
            if filename.endswith(suffix):
                filename = os.path.join(errordir, filename)
                return ErrorReport.read(open(filename, 'rb'))
        return None


globalErrorService = ErrorReportingService()

globalErrorUtility = ProxyFactory(
    removeSecurityProxy(globalErrorService),
    NamesChecker(ILocalErrorReportingService.names())
    )


class ErrorReportRequest:
    implements(IErrorReportRequest)

    oopsid = None

    def setOopsId(self, oopsid):
        """See IErrorReportRequest"""
        self.oopsid = oopsid
