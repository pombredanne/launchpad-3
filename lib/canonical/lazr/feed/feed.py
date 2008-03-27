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

from BeautifulSoup import BeautifulSoup
from datetime import datetime
import pytz
import operator
import os
import time
from urlparse import urljoin
from xml.sax.saxutils import escape as xml_escape

from zope.app.datetimeutils import rfc1123_date
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.component import getUtility
from zope.interface import implements

from canonical.cachedproperty import cachedproperty
from canonical.config import config
# XXX - bac - 2007-09-20, modules in canonical.lazr should not import from
# canonical.launchpad, but we're doing it here as an expediency to get a
# working prototype.  Bug 153795.
from canonical.launchpad.interfaces import ILaunchpadRoot
from canonical.launchpad.webapp import (
    LaunchpadView, canonical_url, urlappend, urlparse)
from canonical.launchpad.webapp.vhosts import allvhosts
from canonical.lazr.interfaces import (
    IFeed, IFeedEntry, IFeedPerson, IFeedTypedData, UnsupportedFeedFormat)

SUPPORTED_FEEDS = ('.atom', '.html')
MINUTES = 60 # Seconds in a minute.


class FeedBase(LaunchpadView):
    """See `IFeed`.

    Base class for feeds.
    """

    implements(IFeed)

    # convert to seconds
    max_age = config.launchpad.max_feed_cache_minutes * MINUTES
    quantity = 25
    items = None
    rootsite = 'mainsite'
    template_files = {'atom': 'templates/feed-atom.pt',
                      'html': 'templates/feed-html.pt'}

    def __init__(self, context, request):
        super(FeedBase, self).__init__(context, request)
        self.format = self.feed_format
        self.root_url = canonical_url(getUtility(ILaunchpadRoot),
                                      rootsite=self.rootsite)

    @property
    def title(self):
        """See `IFeed`."""
        raise NotImplementedError

    @property
    def link_self(self):
        """See `IFeed`."""

        # The self link is the URL for this particular feed.  For example:
        # http://feeds.launchpad.net/ubuntu/announcments.atom
        path = "%s.%s" % (self.feedname, self.format)
        return urlappend(canonical_url(self.context, rootsite="feeds"),
                         path)

    @property
    def site_url(self):
        """See `IFeed`."""
        return allvhosts.configs['mainsite'].rooturl[:-1]

    @property
    def link_alternate(self):
        """See `IFeed`."""
        return canonical_url(self.context, rootsite=self.rootsite)

    @property
    def feed_id(self):
        """See `IFeed`.

        Override this method if the context used does not create a
        meaningful id.
        """
        # Get the creation date, if available.  Otherwise use a fixed date, as
        # allowed by the RFC.
        if hasattr(self.context, 'datecreated'):
            datecreated = self.context.datecreated.date().isoformat()
        elif hasattr(self.context, 'date_created'):
            datecreated = self.context.date_created.date().isoformat()
        else:
            datecreated = "2008"
        url_path = urlparse(self.link_alternate)[2]
        if self.rootsite != 'mainsite':
            id_ = 'tag:launchpad.net,%s:/%s%s' % (
                datecreated,
                self.rootsite,
                url_path)
        else:
            id_ = 'tag:launchpad.net,%s:%s' % (
                datecreated,
                url_path)
        return id_

    def getItems(self):
        """See `IFeed`."""
        if self.items is None:
            self.items = self._getItemsWorker()
        return self.items

    def _getItemsWorker(self):
        """Create the list of items.

        Called by getItems which may cache the results.  The caching is
        necessary since `getItems` is called multiple times in the course of
        constructing a single feed and pulling together the list of items is
        potentially expensive.
        """
        raise NotImplementedError

    @property
    def feed_format(self):
        """See `IFeed`."""
        path = self.request['PATH_INFO']
        extension = os.path.splitext(path)[1]
        if extension in SUPPORTED_FEEDS:
            return extension[1:]
        else:
            raise UnsupportedFeedFormat('%s is not supported' % path)

    @property
    def logo(self):
        """See `IFeed`."""
        raise NotImplementedError

    @property
    def icon(self):
        """See `IFeed`."""
        return "%s/@@/launchpad" % self.site_url

    @cachedproperty
    def date_updated(self):
        """See `IFeed`."""
        sorted_items = sorted(self.getItems(),
                              key=operator.attrgetter('last_modified'),
                              reverse=True)
        if len(sorted_items) == 0:
            # datetime.isoformat() doesn't place the necessary "+00:00"
            # for the feedvalidator's check of the iso8601 date format
            # unless a timezone is specified with tzinfo.
            return datetime.utcnow().replace(tzinfo=pytz.utc)
        last_modified = sorted_items[0].last_modified
        if last_modified is None:
            raise AssertionError, 'All feed entries require a date updated.'
        return last_modified

    def render(self):
        """See `IFeed`."""
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
        """See `IFeed`."""
        self.request.response.setHeader('content-type',
                                        'application/atom+xml;charset=utf-8')
        template_file = ViewPageTemplateFile(self.template_files['atom'])
        result = template_file(self)
        # XXX EdwinGrubbs 2008-01-10 bug=181903
        # Zope3 requires the content-type to start with "text/" if
        # the result is a unicode object.
        return result.encode('utf-8')

    def renderHTML(self):
        """See `IFeed`."""
        return ViewPageTemplateFile(self.template_files['html'])(self)


class FeedEntry:
    """See `IFeedEntry`.

    An individual entry for a feed.
    """

    implements(IFeedEntry)

    def __init__(self,
                 title,
                 link_alternate,
                 date_created,
                 date_updated,
                 date_published=None,
                 authors=None,
                 contributors=None,
                 content=None,
                 id_=None,
                 generator=None,
                 logo=None,
                 icon=None):
        self.title = title
        self.link_alternate = link_alternate
        self.content = content
        self.date_created = date_created
        self.date_updated = date_updated
        self.date_published = date_published
        if date_updated is None:
            raise AssertionError, 'date_updated is required by RFC 4287'
        if authors is None:
            authors = []
        self.authors = authors
        if contributors is None:
            contribuors = []
        self.contributors = contributors
        if id_ is None:
            self.id = self.construct_id()
        else:
            self.id = id_

    @property
    def last_modified(self):
        if self.date_published is not None:
            return max(self.date_published, self.date_updated)
        return self.date_updated

    def construct_id(self):
        url_path = urlparse(self.link_alternate)[2]
        return 'tag:launchpad.net,%s:%s' % (
            self.date_created.date().isoformat(),
            url_path)


class FeedTypedData:
    """Data for a feed that includes its type."""

    implements(IFeedTypedData)

    content_types = ['text', 'html', 'xhtml']

    def __init__(self, content, content_type='text', root_url=None):
        self._content = content
        if content_type not in self.content_types:
            raise UnsupportedFeedFormat("%s: is not valid" % content_type)
        self.content_type = content_type
        self.root_url = root_url

    @property
    def content(self):
        if (self.content_type in ('html', 'xhtml') and
            self.root_url is not None):
            # Unqualified hrefs must be qualified using the original subdomain
            # or they will try be served from http://feeds.launchpad.net,
            # which will not work.
            soup = BeautifulSoup(self._content)
            a_tags = soup.findAll('a')
            for a_tag in a_tags:
                if a_tag['href'].startswith('/'):
                    a_tag['href'] = urljoin(self.root_url, a_tag['href'])
            altered_content = unicode(soup)
        else:
            altered_content = self._content

        if self.content_type in ('text', 'html'):
            altered_content = xml_escape(altered_content)
        elif self.content_type == 'xhtml':
            soup = BeautifulSoup(
                altered_content,
                convertEntities=BeautifulSoup.HTML_ENTITIES)
            altered_content = unicode(soup)
        return altered_content

class FeedPerson:
    """See `IFeedPerson`.

    If this class is consistently used we will not accidentally leak email
    addresses.
    """

    implements(IFeedPerson)

    def __init__(self, person, rootsite):
        self.name = person.displayname
        # We don't want to disclose email addresses in public feeds.
        self.email = None
        self.uri = canonical_url(person, rootsite=rootsite)
