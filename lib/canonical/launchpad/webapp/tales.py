# Copyright 2004 Canonical Ltd.  All rights reserved.
#
"""Implementation of the lp: htmlform: fmt: namespaces in TALES.

"""
__metaclass__ = type

import cgi
import re
import sets
import os.path
import warnings
from zope.interface import Interface, Attribute, implements
from zope.component import getAdapter, queryAdapter

from zope.publisher.interfaces import IApplicationRequest
from zope.publisher.interfaces.browser import IBrowserApplicationRequest
from zope.app.traversing.interfaces import ITraversable
from zope.exceptions import NotFoundError
from canonical.launchpad.interfaces import (
    IPerson, IFacetMenu, IExtraFacetMenu,
    IApplicationMenu, IExtraApplicationMenu, NoCanonicalUrl)
import canonical.lp.dbschema
from canonical.lp import decorates
import canonical.launchpad.pagetitles
from canonical.launchpad.webapp import canonical_url, nearest_menu
from canonical.launchpad.webapp.publisher import get_current_browser_request
from canonical.launchpad.helpers import check_permission


class TraversalError(NotFoundError):
    """XXX Remove this when we upgrade to a more recent Zope x3"""
    # Steve Alexander, Tue Dec 14 13:07:38 UTC 2004


class MenuAPI:
    """Namespace to give access to the facet menus.

       thing/menu:facet       gives the facet menu of the nearest object
                              along the canonical url chain that has an
                              IFacetMenu adapter.

       thing/menu:extrafacet  gives the facet menu of the nearest object
                              along the canonical url chain that has an
                              IFacetMenu adapter.
    """

    def __init__(self, context):
        self._context = context

    def _nearest_menu(self, menutype):
        try:
            return nearest_menu(self._context, menutype)
        except NoCanonicalUrl:
            return None

    def facet(self):
        menu = self._nearest_menu(IFacetMenu)
        if menu is None:
            return []
        else:
            menu.request = get_current_browser_request()
            return list(menu)

    def extrafacet(self):
        menu = self._nearest_menu(IExtraFacetMenu)
        if menu is None:
            return []
        else:
            menu.request = get_current_browser_request()
            return list(menu)

    def _get_selected_facetname(self):
        """Returns the name of the selected facet, or None if there is no
        selected facet.
        """
        facetmenu = self.facet()
        selectedfacetname = None
        for link in facetmenu:
            if link.selected:
                return link.name
        return None

    def application(self):
        selectedfacetname = self._get_selected_facetname()
        if selectedfacetname is None:
            # No facet menu is selected.  So, return empty list.
            return []
        menu = queryAdapter(self._context, IApplicationMenu, selectedfacetname)
        if menu is None:
            return []
        else:
            menu.request = get_current_browser_request()
            return list(menu)

    def extraapplication(self):
        selectedfacetname = self._get_selected_facetname()
        if selectedfacetname is None:
            # No facet menu is selected.  So, return empty list.
            return []
        menu = queryAdapter(
            self._context, IExtraApplicationMenu, selectedfacetname)
        if menu is None:
            return []
        else:
            menu.request = get_current_browser_request()
            return list(menu)


class CountAPI:
    """Namespace to provide counting-related functions, such as length.

    This is available for all objects.  Individual operations may fail for
    objects that do not support them.
    """
    def __init__(self, context):
        self._context = context

    def len(self):
        """somelist/count:len  gives you an int that is len(somelist)."""
        return len(self._context)


class HTMLFormAPI:
    """HTML form helper API, available as request/htmlform:.

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
        'pagetitle',
        'url'
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


class ObjectFormatterAPI:
    """Adapter from any object to a formatted string.  Used for fmt:url."""

    def __init__(self, context):
        self._context = context

    def url(self):
        request = get_current_browser_request()
        return canonical_url(self._context, request)


class DateTimeFormatterAPI:
    """Adapter from datetime objects to a formatted string."""

    def __init__(self, datetimeobject):
        self._datetime = datetimeobject

    def time(self):
        if self._datetime.tzinfo:
            return self._datetime.strftime('%T %Z')
        else:
            return self._datetime.strftime('%T')

    def date(self):
        return self._datetime.strftime('%Y-%m-%d')

    def datetime(self):
        return "%s %s" % (self.date(), self.time())


def clean_path_segments(request):
    """Returns list of path segments, excluding system-related segments."""
    proto_host_port = request.getApplicationURL()
    clean_url = request.getURL()
    clean_path = clean_url[len(proto_host_port):]
    clean_path_split = clean_path.split('/')
    return clean_path_split


class RequestFormatterAPI:
    """Launchpad fmt:... namespace, available for IBrowserApplicationRequest.
    """

    def __init__(self, request):
        self.request = request

    def breadcrumbs(self):
        path_info = self.request.get('PATH_INFO')
        last_path_info_segment = path_info.split('/')[-1]
        clean_path_split = clean_path_segments(self.request)
        last_clean_path_segment = clean_path_split[-1]
        last_clean_path_index = len(clean_path_split) - 1
        if last_clean_path_segment != last_path_info_segment:
            clean_path_split = clean_path_split[:-1]
        L = []
        for index, segment in enumerate(clean_path_split):
            if not (segment.startswith('++vh++') or segment == '++'):
                if not (index == last_clean_path_index
                        and last_path_info_segment == last_clean_path_index):
                    if not segment:
                        segment = 'Launchpad'
                    L.append('<a rel="parent" href="%s">%s</a>' %
                        (self.request.URL[index], segment))
        sep = '<span class="breadcrumbSeparator"> &raquo; </span>'
        return sep.join(L)


class PageTemplateContextsAPI:
    """Adapter from page tempate's CONTEXTS object to fmt:pagetitle.

    This is registered to be used for the dict type.
    """

    implements(ITraversable)

    def __init__(self, contextdict):
        self.contextdict = contextdict

    def traverse(self, name, furtherPath):
        if name == 'pagetitle':
            return self.pagetitle()
        else:
            raise TraversalError(name)

    def pagetitle(self):
        """Return the string title for the page template CONTEXTS dict.

        Take the simple filename without extension from
        self.contextdict['template'].filename, replace any hyphens with
        underscores, and use this to look up a string, unicode or function in
        the module canonical.launchpad.pagetitles.

        If no suitable object is found in canonical.launchpad.pagetitles,
        emit a warning that this page has no title, and return the default
        page title.
        """
        template = self.contextdict['template']
        filename = os.path.basename(template.filename)
        name, ext = os.path.splitext(filename)
        name = name.replace('-', '_')
        titleobj = getattr(canonical.launchpad.pagetitles, name, None)
        if titleobj is None:
            warnings.warn(
                 "No page title in canonical.launchpad.pagetitles for %s"
                 % name)
            return canonical.launchpad.pagetitles.DEFAULT_LAUNCHPAD_TITLE
        elif isinstance(titleobj, basestring):
            return titleobj
        else:
            context = self.contextdict['context']
            view = self.contextdict['view']
            title = titleobj(context, view)
            if title is None:
                return canonical.launchpad.pagetitles.DEFAULT_LAUNCHPAD_TITLE
            else:
                return title


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
            raise TraversalError(name)


class PermissionRequiredQuery:
    """Check if the logged in user has a given permission on a given object.

    Example usage::
        tal:condition="person/required:launchpad.Edit"
    """

    implements(ITraversable)

    def __init__(self, context):
        self.context = context

    def traverse(self, name, furtherPath):
        if len(furtherPath) > 0:
            raise TraversalError(
                    "There should be no further path segments after "
                    "required:permission")
        return check_permission(name, self.context)

