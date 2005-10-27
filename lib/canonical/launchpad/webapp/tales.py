# Copyright 2004 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0613,E0201,R0911
#
"""Implementation of the lp: htmlform: fmt: namespaces in TALES.

"""
__metaclass__ = type

import bisect
import cgi
import re
import os.path

from zope.interface import Interface, Attribute, implements
from zope.component import getUtility, queryAdapter, getDefaultViewName

from zope.publisher.interfaces import IApplicationRequest
from zope.publisher.interfaces.browser import IBrowserApplicationRequest
from zope.app.traversing.interfaces import ITraversable
from zope.exceptions import NotFoundError
from zope.security.interfaces import Unauthorized
from zope.security.proxy import isinstance as zope_isinstance

from canonical.launchpad.interfaces import (
    IPerson, ILaunchBag, IFacetMenu, IApplicationMenu, IContextMenu,
    NoCanonicalUrl, IBugSet)
from canonical.lp import dbschema
import canonical.launchpad.pagetitles
from canonical.launchpad.webapp import canonical_url, nearest_menu
from canonical.launchpad.webapp.menu import Url
from canonical.launchpad.webapp.publisher import get_current_browser_request
from canonical.launchpad.helpers import check_permission


class TraversalError(NotFoundError):
    """XXX Remove this when we upgrade to a more recent Zope x3"""
    # Steve Alexander, Tue Dec 14 13:07:38 UTC 2004


class MenuAPI:
    """Namespace to give access to the facet menus.

       CONTEXTS/menu:facet       gives the facet menu of the nearest object
                                 along the canonical url chain that has an
                                 IFacetMenu adapter.

    """

    def __init__(self, context):
        if zope_isinstance(context, dict):
            # We have what is probably a CONTEXTS dict.
            # We get the context out of here, and use that for self.context.
            # We also want to see if the view has a __launchpad_facetname__
            # attribute.
            self._context = context['context']
            view = context['view']
            self._request = context['request']
            self._selectedfacetname = getattr(
                view, '__launchpad_facetname__', None)
        else:
            self._context = context
            self._request = get_current_browser_request()
            self._selectedfacetname = None

    def _nearest_menu(self, menutype):
        try:
            return nearest_menu(self._context, menutype)
        except NoCanonicalUrl:
            return None

    def _requesturl(self):
        request = self._request
        if request is None:
            return None
        requesturlobj = Url(request.getURL(), request.get('QUERY_STRING'))
        # If the default view name is being used, we will want the url
        # without the default view name.
        defaultviewname = getDefaultViewName(self._context, request)
        if requesturlobj.pathnoslash.endswith(defaultviewname):
            requesturlobj = Url(request.getURL(1), request.get('QUERY_STRING'))
        return requesturlobj

    def facet(self):
        menu = self._nearest_menu(IFacetMenu)
        if menu is None:
            return []
        else:
            return list(menu.iterlinks(
                requesturl=self._requesturl(),
                selectedfacetname=self._selectedfacetname))

    def application(self):
        selectedfacetname = self._selectedfacetname
        if selectedfacetname is None:
            # No facet menu is selected.  So, return empty list.
            return []
        menu = queryAdapter(self._context, IApplicationMenu, selectedfacetname)
        if menu is None:
            return []
        else:
            return list(menu.iterlinks(requesturl=self._requesturl()))

    def context(self):
        menu = IContextMenu(self._context, None)
        if menu is None:
            return  []
        else:
            return list(menu.iterlinks(requesturl=self._requesturl()))


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


class EnumValueAPI:
    """Namespace to test whether a DBSchema Item has a particular value.

    The value is given in the next path step.

        tal:condition="somevalue/enumvalue:BISCUITS"

    Registered for canonical.lp.dbschema.Item.
    """
    implements(ITraversable)

    def __init__(self, item):
        self.item = item

    def traverse(self, name, furtherPath):
        if self.item.name == name:
            return True
        else:
            # Check whether this was an allowed value for this dbschema.
            schema = self.item.schema
            try:
                schema.items[name]
            except KeyError:
                raise TraversalError(
                    'The %s dbschema does not have a value %s.' %
                    (schema.__name__, name))
            return False


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

    _all = {}
    for name in dbschema.__all__:
        schema = getattr(dbschema, name)
        if (schema is not dbschema.DBSchema and
            issubclass(schema, dbschema.DBSchema)):
            _all[name] = schema

    def __init__(self, number):
        self._number = number

    def traverse(self, name, furtherPath):
        if name in self._all:
            return self._all[name].items[self._number].title
        else:
            raise TraversalError(name)


class NoneFormatter:
    """Adapter from None to various string formats.

    In general, these will return an empty string.  They are provided for ease
    of handling NULL values from the database, which become None values for
    attributes in content classes.
    """
    implements(ITraversable)

    allowed_names = set([
        'nl_to_br',
        'nice_pre',
        'breadcrumbs',
        'date',
        'time',
        'datetime',
        'exactduration',
        'approximateduration',
        'pagetitle',
        'text-to-html',
        'url',
        'icon'
        ])

    def __init__(self, context):
        self.context = context

    def traverse(self, name, furtherPath):
        if name == 'shorten':
            if len(furtherPath) == 0:
                raise TraversalError(
                    "you need to traverse a number after fmt:shorten")
            maxlength = int(furtherPath.pop())
            # XXX: why is maxlength not used here at all?
            #       - kiko, 2005-08-24
            return ''
        elif name in self.allowed_names:
            return ''
        else:
            raise TraversalError, name


class ObjectFormatterAPI:
    """Adapter from any object to a formatted string.

    Used for fmt:url.
    """

    def __init__(self, context):
        self._context = context

    def url(self):
        request = get_current_browser_request()
        return canonical_url(self._context, request)


class BugTaskFormatterAPI(ObjectFormatterAPI):
    """Adapter for IBugTask objects to a formatted string.

    Used for fmt:icon.
    """

    def icon(self):
        """Return the appropriate <img> tag for the bugtask icon.

        The icon displayed is calculated based on the IBugTask.priority.
        """
        if self._context.priority:
            priority_title = self._context.priority.title.lower()
        else:
            priority_title = None

        if not priority_title:
            return '<img alt="(no priority)" title="no priority" src="/@@/bug" />'
        elif priority_title == 'wontfix':
            # Special-case Wontfix by returning the "generic" bug icon
            # because we actually hope to eliminate Wontfix
            # entirely. See
            # https://wiki.launchpad.canonical.com/SimplifyingMalone
            return '<img alt="(wontfix priority)" title="wontfix" src="/@@/bug" />'
        else:
            return '<img alt="(%s priority)" title="%s priority" src="/@@/bug-%s" />' % (priority_title, priority_title, priority_title)


class MilestoneFormatterAPI(ObjectFormatterAPI):
    """Adapter for IMilestone objects to a formatted string.

    Used for fmt:icon.
    """

    def icon(self):
        """Return the appropriate <img> tag for the milestone icon."""
        return '<img alt="" src="/++resource++target" />'


class DateTimeFormatterAPI:
    """Adapter from datetime objects to a formatted string."""

    def __init__(self, datetimeobject):
        self._datetime = datetimeobject

    def time(self):
        if self._datetime.tzinfo:
            value = self._datetime.astimezone(getUtility(ILaunchBag).timezone)
            return value.strftime('%T %Z')
        else:
            return self._datetime.strftime('%T')

    def date(self):
        value = self._datetime
        if value.tzinfo:
            value = value.astimezone(getUtility(ILaunchBag).timezone)
        return value.strftime('%Y-%m-%d')

    def datetime(self):
        return "%s %s" % (self.date(), self.time())


class DurationFormatterAPI:
    """Adapter from timedelta objects to a formatted string."""

    def __init__(self, duration):
        self._duration = duration

    def exactduration(self):
        """Format timedeltas as "v days, w hours, x minutes, y.z seconds"."""
        parts = []
        minutes, seconds = divmod(self._duration.seconds, 60)
        hours, minutes = divmod(minutes, 60)
        seconds = seconds + (float(self._duration.microseconds) / 10**6)
        if self._duration.days > 0:
            if self._duration.days == 1:
                parts.append('%d day' % self._duration.days)
            else:
                parts.append('%d days' % self._duration.days)
        if parts or hours > 0:
            if hours == 1:
                parts.append('%d hour' % hours)
            else:
                parts.append('%d hours' % hours)
        if parts or minutes > 0:
            if minutes == 1:
                parts.append('%d minute' % minutes)
            else:
                parts.append('%d minutes' % minutes)
        if parts or seconds > 0:
            parts.append('%0.1f seconds' % seconds)

        return ', '.join(parts)

    def approximateduration(self):
        """Return a nicely-formatted approximate duration.

        E.g. 'an hour', 'three minutes', '1 hour 10 minutes' and so
        forth.

        See https://wiki.launchpad.canonical.com/PresentingLengthsOfTime.
        """
        # NOTE: There are quite a few "magic numbers" in this
        # implementation; they are generally just figures pulled
        # directly out of the PresentingLengthsOfTime spec, and so
        # it's not particularly easy to give each and every number of
        # a useful name. It's also unlikely that these numbers will be
        # changed.

        # Calculate the total number of seconds in the duration,
        # including the decimal part.
        seconds = self._duration.days * (3600 * 24)
        seconds += self._duration.seconds
        seconds += (float(self._duration.microseconds) / 10**6)

        # First we'll try to calculate an approximate number of
        # seconds up to a minute. We'll start by defining a sorted
        # list of (boundary, display value) tuples.  We want to show
        # the display value corresponding to the lowest boundary that
        # 'seconds' is less than, if one exists.
        representation_in_seconds = (
            (1.5, '1 second'),
            (2.5, '2 seconds'),
            (3.5, '3 seconds'),
            (4.5, '4 seconds'),
            (7.5, '5 seconds'),
            (12.5, '10 seconds'),
            (17.5, '15 seconds'),
            (22.5, '20 seconds'),
            (27.5, '25 seconds'),
            (35, '30 seconds'),
            (45, '40 seconds'),
            (55, '50 seconds'),
            (90, 'a minute'),
        )

        # Break representation_in_seconds into two pieces, to simplify
        # finding the correct display value, through the use of the
        # built-in bisect module.
        second_boundaries, display_values = zip(*representation_in_seconds)

        # Is seconds small enough that we can produce a representation
        # in seconds (up to 'a minute'?)
        if seconds < second_boundaries[-1]:
            # Use the built-in bisection algorithm to locate the index
            # of the item which "seconds" sorts after.
            matching_element_index = bisect.bisect(second_boundaries, seconds)

            # Return the corresponding display value.
            return display_values[matching_element_index]

        # More than a minute, approximately; our calculation strategy
        # changes. From this point forward, we may also need a
        # "verbal" representation of the number. (We never need a
        # verbal representation of "1", because we tend to special
        # case the number 1 for various approximations, and we usually
        # use a word like "an", instead of "one", e.g. "an hour")
        number_name = {
            2: 'two', 3: 'three', 4: 'four', 5: 'five',
            6: 'six', 7: 'seven', 8: 'eight', 9: 'nine',
            10: 'ten'}

        # Convert seconds into minutes, and round it.
        minutes, remaining_seconds = divmod(seconds, 60)
        minutes += remaining_seconds / 60.0
        minutes = int(round(minutes))

        if minutes <= 59:
            number_as_text = number_name.get(minutes, str(minutes))
            return number_as_text + " minutes"

        # Is the duration less than an hour and 5 minutes?
        if seconds < (60 + 5) * 60:
            return "an hour"

        # Next phase: try and calculate an approximate duration
        # greater than one hour, but fewer than ten hours, to a 10
        # minute granularity.
        hours, remaining_seconds = divmod(seconds, 3600)
        ten_minute_chunks = int(round(remaining_seconds / 600.0))
        minutes = ten_minute_chunks * 10
        hours += (minutes / 60)
        minutes %= 60
        if hours < 10:
            if minutes:
                # If there is a minutes portion to display, the number
                # of hours is always shown as a digit.
                if hours == 1:
                    return "1 hour %s minutes" % minutes
                else:
                    return "%d hours %s minutes" % (hours, minutes)
            else:
                number_as_text = number_name.get(hours, str(hours))
                return "%s hours" % number_as_text

        # Is the duration less than ten and a half hours?
        if seconds < (10.5 * 3600):
            return 'ten hours'

        # Try to calculate the approximate number of hours, to a
        # maximum of 47.
        hours = int(round(seconds / 3600.0))
        if hours <= 47:
            return "%d hours" % hours

        # Is the duration fewer than two and a half days?
        if seconds < (2.5 * 24 * 3600):
            return 'two days'

        # Try to approximate to day granularity, up to a maximum of 13
        # days.
        days = int(round(seconds / (24 * 3600)))
        if days <= 13:
            return "%s days" % number_name.get(days, str(days))

        # Is the duration fewer than two and a half weeks?
        if seconds < (2.5 * 7 * 24 * 3600):
            return 'two weeks'

        # If we've made it this far, we'll calculate the duration to a
        # granularity of weeks, once and for all.
        weeks = int(round(seconds / (7 * 24 * 3600.0)))
        return "%s weeks" % number_name.get(weeks, str(weeks))


def clean_path_segments(request):
    """Returns list of path segments, excluding system-related segments."""
    proto_host_port = request.getApplicationURL()
    clean_url = request.getURL()
    clean_path = clean_url[len(proto_host_port):]
    clean_path_split = clean_path.split('/')
    return clean_path_split


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
            # sabdfl 25/0805 page titles are now mandatory hence the assert
            raise AssertionError(
                 "No page title in canonical.launchpad.pagetitles for %s"
                 % name)
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

    @staticmethod
    def _substitute_matchgroup_for_spaces(match):
        """Return a string made up of '&nbsp;' for each character in the
        first match group.

        Used when replacing leading spaces with nbsps.

        There must be only one match group.
        """
        groups = match.groups()
        assert len(groups) == 1
        return '&nbsp;' * len(groups[0])

    @staticmethod
    def _linkify_substitution(match):
        if match.group('bug') is not None:
            bugnum = match.group('bugnum')
            # Use a hardcoded url so we still have a link for bugs that don't
            # exist, or are private.
            # XXX SteveAlexander 2005-07-14, I can't get a canonical_url for
            #     a private bug.  I should be able to do so.
            url = '/malone/bugs/%s' % bugnum
            # The text will have already been cgi escaped.
            text = match.group('bug')
            bugset = getUtility(IBugSet)
            try:
                bug = bugset.get(bugnum)
            except NotFoundError:
                title = "No such bug"
            else:
                try:
                    title = bug.title
                except Unauthorized:
                    title = "private bug"
            title = cgi.escape(title, quote=True)
            return '<a href="%s" title="%s">%s</a>' % (url, title, text)
        elif match.group('url') is not None:
            # The text will already have been cgi escaped.
            # We still need to escape quotes for the url.
            url = match.group('url')
            # The url might end in a spurious &gt;.  If so, remove it
            # and put it outside the url text.
            trail = ''
            gt = ''
            if url[-1] in (",", ".", "?", ":") or url[-2:] == ";;":
                # These common punctuation symbols often trail URLs; we
                # deviate from the specification slightly here but end
                # up with less chance of corrupting a URL because
                # somebody added punctuation after it in the comment.
                #
                # The special test for ";;" is done to catch the case
                # where the URL is wrapped in greater/less-than and
                # then followed with a semicolon. We can't just knock
                # off a trailing semi-colon because it might have been
                # part of an entity -- and that's what the next clauses
                # handle.
                trail = url[-1]
                url = url[:-1]
            if url.lower().endswith('&gt;'):
                gt = url[-4:]
                url = url[:-4]
            elif url.endswith(";"):
                # This is where a single semi-colon is consumed, for
                # the case where the URL didn't end in an entity.
                trail = url[-1]
                url = url[:-1]
            return '<a rel="nofollow" href="%s">%s</a>%s%s' % (
                url.replace('"', '&quot;'), url, gt, trail)
        else:
            raise AssertionError("Unknown pattern matched.")

    # match whitespace at the beginning of a line
    _re_leadingspace = re.compile(r'^(\s+)')

    # Match urls or bugs.
    _re_linkify = re.compile(r'''
      (?P<url>
        (?:about|gopher|http|https|ftp|mailto|file|irc|jabber):[/]*
        (?P<host>[a-zA-Z0-9:@_\-\.]+)
        (?P<urlchars>[a-zA-Z0-9/:;@_%~#=&\.\-\?\+\$,]*)
      ) |
      (?P<bug>
        bug\s*(?:\#|number\.?|num\.?|no\.?)?\s*
        0*(?P<bugnum>\d+)
      )
    ''', re.IGNORECASE | re.VERBOSE)

    @staticmethod
    def _split_paragraphs(text):
        """Split text into paragraphs.

        This function yields lists of strings that represent
        paragraphs of text.

        Paragraphs are split by one or more blank lines.

        Each paragraph is further split into one or more logical lines
        of text.  Two adjacent lines are considered to be part of the
        same logical line if the following conditions hold:
          1. the first line is between 60 and 80 characters long
          2. the second line does not begin with whitespace.
        """
        paragraph = []
        continue_logical_line = False
        for line in text.splitlines():
            line = line.rstrip()

            # blank lines split paragraphs
            if not line:
                if paragraph:
                    yield paragraph
                paragraph = []
                continue_logical_line = False
                continue

            # continue the run of text if the last line was between 60
            # and 80 characters, and this line doesn't begin with
            # whitespace.
            if continue_logical_line and not line[0].isspace():
                paragraph[-1] += '\n' + line
            else:
                paragraph.append(line)

            continue_logical_line = 60 < len(line) < 80
        if paragraph:
            yield paragraph

    def text_to_html(self):
        """Quote text according to DisplayingParagraphsOfText."""
        # This is based on the algorithm in the
        # DisplayingParagraphsOfText spec, but is a little more
        # complicated.

        # 1. Blank lines are used to detect paragraph boundaries.
        # 2. Two lines are considered to be part of the same logical line
        #    only if the first is between 60 and 80 characters and the
        #    second does not begin with white space.
        # 3. Use <br /> to split logical lines within a paragraph.

        output = []
        first_para = True
        for para in self._split_paragraphs(self._stringtoformat):
            if not first_para:
                output.append('\n')
            first_para = False
            output.append('<p>')
            first_line = True
            for line in para:
                if not first_line:
                    output.append('<br />\n')
                first_line = False
                # escape ampersands, etc in text
                line = cgi.escape(line)
                # convert leading space in logical line to non-breaking space
                line = self._re_leadingspace.sub(
                    self._substitute_matchgroup_for_spaces, line)
                output.append(line)
            output.append('</p>')

        text = ''.join(output)

        # Linkify the text.
        text = self._re_linkify.sub(self._linkify_substitution, text)

        return text

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
        """Use like tal:content="context/foo/fmt:shorten/60"."""
        if len(self._stringtoformat) > maxlength:
            return '%s...' % self._stringtoformat[:maxlength-3]
        else:
            return self._stringtoformat

    def traverse(self, name, furtherPath):
        if name == 'nl_to_br':
            return self.nl_to_br()
        elif name == 'text-to-html':
            return self.text_to_html()
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

