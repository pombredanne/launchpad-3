# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Base classes for feeds.

Supported feeds include Atom, Javascript, and HTML-snippets.
Future support may include feeds such as sparklines.
"""

__metaclass__ = type

__all__ = [
    'FeedBase',
    'FeedEntry',
    'FeedPerson',
    'FeedTypedData',
    'MINUTES',
    ]

import operator
import os
import time

from zope.app.datetimeutils import rfc1123_date
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.interface import implements

from canonical.cachedproperty import cachedproperty
# XXX - bac - 2007-09-20, modules in canonical.lazr should not import from
# canonical.launchpad, but we're doing it here as an expediency to get a
# working prototype.  Bug 153795.
from canonical.launchpad.webapp import canonical_url, LaunchpadFormView
from canonical.launchpad.webapp.vhosts import allvhosts
from canonical.lazr.interfaces import (
    IFeed, IFeedPerson, IFeedTypedData, UnsupportedFeedFormat)

MINUTES = 60
MAX_AGE = 60 * MINUTES
SUPPORTED_FEEDS = ('atom', 'html')

class FeedBase(LaunchpadFormView):
    """Base class for feeds."""

    implements(IFeed)

    # XXX - bac 2-Oct-2007 - Bug 153785 - these values should be in a config file.
    max_age = MAX_AGE
    quantity = 25
    items = None
    template_files = {'atom': 'templates/feed-atom.pt',
                      'html': 'templates/feed-html.pt'}

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.format = self.feed_format

    def initialize(self):
        """Override this in subclasses.

        Default implementation does nothing.
        """
        pass

    @property
    def title(self):
        """Return the title of the feed."""
        raise NotImplementedError

    @property
    def url(self):
        """Return the URL for the feed.  It should be unique and permanent."""
        raise NotImplementedError

    @property
    def site_url(self):
        """Return the URL for the main site of Launchpad."""
        return allvhosts.configs['mainsite'].rooturl[:-1]

    def getItems(self):
        """Get the individual unformatted items for the feed."""
        raise NotImplementedError

    def itemToFeedEntry(self, item):
        """Convert a single item to a formatted feed entry."""
        raise NotImplementedError

    @property
    def feed_format(self):
        """Return the requested feed format.

        Raises UnsupportedFeedFormat if the format is not supported.
        """
        path = self.request['PATH_INFO']
        extension = os.path.splitext(path)[1]
        if len(extension) > 0 and extension[1:] in SUPPORTED_FEEDS:
            return extension[1:]
        else:
            raise UnsupportedFeedFormat('%s is not supported' % path)

    @property
    def logo(self):
        """Get the URL for the feed logo."""
        raise NotImplementedError

    @property
    def icon(self):
        """Get the icon for the feed."""
        return "%s/@@/launchpad" % self.site_url

    @cachedproperty
    def date_updated(self):
        """Get the update time for the feed.

        By default this is set to the most recent update of the entries in the
        feed.
        """
        sorted_items = sorted(self.getItems(),
                              key=operator.attrgetter('date_updated'),
                              reverse=True)
        if len(sorted_items) == 0:
            return None
        return sorted_items[0].date_updated

    def render(self):
        """Render the feed."""
        expires = rfc1123_date(time.time() + self.max_age)
        if self.date_updated is not None:
            last_modified = rfc1123_date(
                time.mktime(self.date_updated.timetuple()))
        else:
            last_modified = rfc1123_date(time.time())
        response = self.request.response
        response.setHeader('Expires', expires)
        response.setHeader('Cache-Control', 'max-age=%d' % self.max_age)
        response.setHeader('X-Cache-Control', 'max-age=%d' % self.max_age)
        response.setHeader('Last-Modified', last_modified)

        if self.format == 'atom':
            return self.renderAtom()
        elif self.format == 'html':
            return self.renderHTML()
        else:
            raise UnsupportedFeedFormat("Format %s is not supported" %
                                        self.format)

    def renderAtom(self):
        """Render the object as an Atom feed.

        Override this as opposed to overriding render().
        """
        return ViewPageTemplateFile(self.template_files['atom'])(self)

    def renderHTML(self):
        """Render the object as an html feed.

        Override this as opposed to overriding render().
        """
        return ViewPageTemplateFile(self.template_files['html'])(self)


class FeedEntry:
    """An entry for a feed."""
    def __init__(self,
                 title,
                 id_,
                 link_alternate,
                 date_updated=None,
                 date_published=None,
                 authors=None,
                 contributors=None,
                 content=None,
                 generator=None,
                 logo=None,
                 icon=None):
        self.title = title
        self.link_alternate = link_alternate
        self.content = content
        self.date_published = date_published
        self.date_updated = date_updated
        if authors is None:
            authors = []
        self.authors = authors
        if contributors is None:
            contribuors = []
        self.contributors = contributors
        self.id = id_


class FeedTypedData:
    """Data for a feed that includes its type."""

    implements(IFeedTypedData)

    content_types = ['text', 'html', 'xhtml']
    def __init__(self, content, content_type='text'):
        self.content = content
        if content_type not in self.content_types:
            raise ValueError, "%s: is not valid" % content_type
        self.content_type = content_type


class FeedPerson:
    """Data for person in a feed.

    If this class is consistently used we will not accidentally leak email
    addresses.
    """

    implements(IFeedPerson)

    def __init__(self, person, rootsite):
        self.name = person.displayname
        # We don't want to disclose email addresses in public feeds.
        self.email = None
        self.uri = canonical_url(person, rootsite=rootsite)
