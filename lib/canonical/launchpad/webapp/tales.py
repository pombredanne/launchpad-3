# Copyright 2004 Canonical Ltd.  All rights reserved.
#
"""Implementation of the lp: htmlform: fmt: namespaces in TALES.

"""
__metaclass__ = type

import cgi
import re
import sets
from zope.interface import Interface, Attribute, implements

from zope.publisher.interfaces import IApplicationRequest
from zope.publisher.interfaces.browser import IBrowserApplicationRequest
from zope.app.traversing.interfaces import ITraversable
from zope.exceptions import NotFoundError
from canonical.launchpad.interfaces import IPerson
import canonical.lp.dbschema

class TraversalError(NotFoundError):
    """XXX Remove this when we upgrade to a more recent Zope x3"""
    # Steve Alexander, Tue Dec 14 13:07:38 UTC 2004

class HTMLFormAPI:
    """HTML form helper API, available as request:htmlform.

    Use like:

        request/htmlform:fieldname/selected/literalvalue

        if request.form[fieldname] == literalvalue:
            return "selected"
        else:
            return None

    """
    implements(ITraversable)
    __used_for__ = IBrowserApplicationRequest

    def __init__(self, request):
        self.form = request.form

    def traverse(self, name, furtherPath):
        if len(furtherPath) == 1:
            operation = furtherPath.pop()
            return HTMLFormOperation(self.form.get(name), operation)
        else:
            operation = furtherPath.pop()
            value = furtherPath.pop()
            if htmlmatch(self.form.get(name), value):
                return operation
            else:
                return None

def htmlmatch(formvalue, value):
    value = str(value)
    if isinstance(formvalue, list):
        return value in formvalue
    else:
        return formvalue == value

class HTMLFormOperation:

    implements(ITraversable)

    def __init__(self, formvalue, operation):
        self.formvalue = formvalue
        self.operation = operation

    def traverse(self, name, furtherPath):
        if htmlmatch(self.formvalue, name):
            return self.operation
        else:
            return None


class IRequestAPI(Interface):
    """Launchpad lp:... API available for an IApplicationRequest."""

    person = Attribute("The IPerson for the request's principal.")


class RequestAPI:
    """Adapter from IApplicationRequest to IRequestAPI."""
    implements(IRequestAPI)

    __used_for__ = IApplicationRequest

    def __init__(self, request):
        self.request = request

    def person(self):
        return IPerson(self.request.principal, None)
    person = property(person)


class DBSchemaAPI:
    """Adapter from integers to things that can extract information from
    DBSchemas.
    """
    implements(ITraversable)
    _all = dict([(name, getattr(canonical.lp.dbschema, name))
                 for name in canonical.lp.dbschema.__all__])

    def __init__(self, number):
        self._number = number

    def traverse(self, name, furtherPath):
        if name in self._all:
            return self._all[name].items[self._number].title
        else:
            raise TraversalError, name


class NoneFormatter:
    """Adapter from None to various string formats.

    In general, these will return an empty string.  They are provided for ease
    of handling NULL values from the database, which become None values for
    attributes in content classes.
    """
    implements(ITraversable)

    allowed_names = sets.Set([
        'nl_to_br',
        'nice_pre',
        'breadcrumbs',
        'date',
        'time',
        'datetime',
        ])

    def __init__(self, context):
        self.context = context

    def traverse(self, name, furtherPath):
        if name == 'shorten':
            if len(furtherPath) == 0:
                raise TraversalError(
                    "you need to traverse a number after fmt:shorten")
            maxlength = int(furtherPath.pop())
            return ''
        elif name in self.allowed_names:
            return ''
        else:
            raise TraversalError, name


class DateTimeFormatterAPI:
    """Adapter from datetime objects to a formatted string.

    If the datetime object is None, for example from a NULL column in
    the database, then the methods that would return a formatted
    string instead return None.

    This allows you to say::

      <span tal:content="some_datetime/fmt:date | default">Not known</span>

    """

    def __init__(self, datetimeobject):
        self._datetime = datetimeobject

    def time(self):
        return self._datetime.strftime('%T')

    def date(self):
        return self._datetime.strftime('%Y-%m-%d')

    def datetime(self):
        return "%s %s" % (self.date(), self.time())


class RequestFormatterAPI:
    """Launchpad fmt:... namespace, available for IBrowserApplicationRequest.
    """

    def __init__(self, request):
        self.request = request

    def breadcrumbs(self):
        path_info = self.request.get('PATH_INFO')
        last_path_info_segment = path_info.split('/')[-1]
        proto_host_port = self.request.getApplicationURL()
        clean_url = self.request.getURL()
        clean_path = clean_url[len(proto_host_port):]
        clean_path_split = clean_path.split('/')
        last_clean_path_segment = clean_path_split[-1]
        last_clean_path_index = len(clean_path_split) - 1
        if last_clean_path_segment != last_path_info_segment:
            clean_path = '/'.join(clean_path_split[:-1])
        L = []
        for index, segment in enumerate(clean_path.split('/')):
            if not (segment.startswith('++vh++') or segment == '++'):
                if not (index == last_clean_path_index
                        and last_path_info_segment == last_clean_path_index):
                    ##import pdb; pdb.set_trace()
                    if not segment:
                        segment = 'Launchpad'
                    L.append('<a rel="parent" href="%s">%s</a>' %
                        (self.request.URL[index], segment))
        sep = '<span class="breadcrumbSeparator"> &raquo; </span>'
        return sep.join(L)


class FormattersAPI:
    """Adapter from strings to HTML formatted text."""

    implements(ITraversable)

    def __init__(self, stringtoformat):
        self._stringtoformat = stringtoformat

    def nl_to_br(self):
        """Quote HTML characters, then replace newlines with <br /> tags."""
        return cgi.escape(self._stringtoformat).replace('\n','<br />\n')

    def nice_pre(self):
        """<pre>, except the browser knows it is allowed to break long lines

        Note that CSS will eventually have a property to specify this
        behaviour, but we want this now. To do this we need to use the mozilla
        specific -moz-pre-wrap value of the white-space property. We try to
        fall back for IE by using the IE specific word-wrap property.

        TODO: Test IE compatibility. StuartBishop 20041118
        TODO: This should probably just live in the stylesheet if this
            CSS implementation is good enough. StuartBishop 20041118
        """
        if not self._stringtoformat:
            return self._stringtoformat
        else:
            return ('<pre style="'
                    'white-space: -moz-pre-wrap;'
                    'white-space: -o-pre-wrap;'
                    'word-wrap: break-word;'
                    '">%s</pre>'
                    % cgi.escape(self._stringtoformat)
                    )

    def shorten(self, maxlength):
        """Use like tal:content="context/foo/fmt:shorten/60"""
        if len(self._stringtoformat) > maxlength:
            return '%s...' % self._stringtoformat[:maxlength-3]
        else:
            return self._stringtoformat

    def traverse(self, name, furtherPath):
        if name == 'nl_to_br':
            return self.nl_to_br()
        elif name == 'nice_pre':
            return self.nice_pre()
        elif name == 'shorten':
            if len(furtherPath) == 0:
                raise TraversalError(
                    "you need to traverse a number after fmt:shorten")
            maxlength = int(furtherPath.pop())
            return self.shorten(maxlength)
        else:
            raise TraversalError, name

