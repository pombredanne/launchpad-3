# Copyright 2004 Canonical Ltd.  All rights reserved.
#
"""Implementation of the lp: and htmlform: namespaces in TALES.

"""
__metaclass__ = type

import cgi, re
from zope.interface import Interface, Attribute, implements

from zope.publisher.interfaces import IApplicationRequest
from zope.publisher.interfaces.browser import IBrowserApplicationRequest
from zope.app.traversing.interfaces import ITraversable
from zope.exceptions import NotFoundError
from canonical.launchpad.interfaces import IPerson
import canonical.lp.dbschema

class TraversalError(NotFoundError):
    """XXX Remove this when we upgrade to a more recent Zope x3"""


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
            return self._all[name]._items[self._number].title
        else:
            raise TraversalError, name


class FormattersAPI:
    """Adapter from strings to HTML formatted text."""

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

        TODO: Test IE compatibility. StuartBishop 2004/11/18
        TODO: This should probably just live in the stylesheet if this
            CSS implementation is good enough.
        """

        return (
                '<div style="font-family: monospace; '
                'white-space: pre; '
                'white-space: -moz-pre-wrap; white-space: -o-pre-wrap; '
                'word-wrap: break-word;">%s</div>' % self.nl_to_br()
                )

