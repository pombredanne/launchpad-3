# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces for feeds generation."""

__metaclass__ = type

__all__ = [
    'IFeed',
    'IFeedEntry',
    'IFeedPerson',
    'IFeedTypedData',
    'UnsupportedFeedFormat',
    ]

from zope.interface import Interface
from zope.schema import Datetime, Int, List, Text, TextLine, URI


class UnsupportedFeedFormat(Exception):
    """The requested feed format is not supported."""


class IFeed(Interface):
    """Interface for feeds.

    Feeds in Launchpad are published using the Atom syndication standard, as
    defined by the proposed standard RFC 4287[1] or as HTML snippets.

    An Atom feed is an XML document consisting of a feed and zero or more
    entries.  The feed section describes the feed as a whole while the entries
    are descriptions of the individual components of that feed.  For instance
    the feed for "feeds.launchpad.net/ubuntu/announcement.atom" has metadata
    referring to the Ubuntu project and each entry in the feed represents a
    specific announcement.

    The components of IFeed are those data specifically for the feed.  The
    entry data is found in IFeedEntry.

    [1] http://tools.ietf.org/html/rfc4287
    """

    # Given the polling nature of feed readers it is important that feed data
    # be cached to minimize load on the application servers.  Each feed can
    # give hints as to how long it should be cached.  'max_age' is the
    # duration in seconds the feed should be cached before being considered
    # stale.
    max_age = Int(
        title=u"Maximum age",
        description=u"Maximum age in seconds for a feed to be cached.")

    # A feed could contain an arbitrary large number of entries, so a quantity
    # may be specified to limit the number of entries returned.
    quantity = Int(
        title=u"Quantity",
        description=u"Number of items to be returned in a feed.")

    # The title of the feed is prominently displayed in readers and should
    # succinctly identify the feed, e.g. "Latest bugs in Kubuntu".
    title = TextLine(
        title=u"Title of the feed.")

    # The URL for a feed identifies it uniquely and it should never change.
    # The latest bugs in Kubuntu is:
    # http://feeds.launchpad.net/kubuntu/latest-bugs.atom
    url = TextLine(
        title=u"URL for the feed.",
        description=u"The URL for the feed should be unique and permanent.")

    # The site URL refers to the top-level page for the site serving the
    # feed.  For Launchpad the site_url should be the mainsite URL,
    # i.e. http://launchpad.net.
    site_url = TextLine(
        title=u"Site URL",
        description=u"The URL for the main site of Launchpad.")

    # Feeds are intended to be machine-readable -- XML to be processed by a
    # feed reader and then, possibly, displayed.  The alternate URL is the
    # location of the human-readable equivalent for the feed.  For Ubuntu
    # announcements the alternate location is
    # http://launchpad.net/ubuntu/+announcements.
    alternate_url = TextLine(
        title=u"Alternate URL for the feed.",
        description=u"The URL to a resource that is the human-readable "
                     "equivalent of the feed.  So for: "
                     "http://feeds.launchpad.net/ubuntu/announcements.atom "
                     "the alternate_url would be: "
                     "http://launchpad.net/ubuntu/+announcements")

    # The feed ID is a permanent ID for the feed and it must be unique across
    # all time and domains.  That sounds harder than it really is.  To make
    # our IDs unique we follow the Tag ID standard proposed in RFC 4151 which
    # composes an ID using 'tag:' + domain + creation date + unique URL path.
    # So an ID for a Jokosher announcment feed would look like:
    # tag:launchpad.net,2006-5-26:/jokosher/+announcements.
    feed_id = TextLine(
        title=u"ID for the feed.",
        description=u"The <id> for a feed is permanent and globally unique. "
                     "It is constructed following RFC 4151.")

    # The feed format is either 'atom' or 'html'.
    feed_format = TextLine(
        title=u"Feed format",
        description=u"Requested feed format.  "
                     "Raises UnsupportedFeed if not supported.")

    # The logo URL points to an image identifying the feed and will likely
    # vary from one Launchpad application to another.  For example the logo
    # for bugs is:
    # http://launchpad.net/@@/bug.
    logo = TextLine(
        title=u"Logo URL",
        description=u"The URL for the feed logo.")

    # The icon URL points to an image identifying the feed.  For Launchpad
    # feeds the icon is http://launchpad.net/@@/launchpad.
    icon = TextLine(
        title=u"Icon URL",
        description=u"The URL for the feed icon.")

    # The date updated represents the last date any information in the feed
    # changed.  For instance for feed for Launchpad announcements the date
    # updated is the most recent date any of the announcements presented in
    # the feed changed.  Feed readers use the date updated one criteria as to
    # whether to fetch the feed information anew.
    date_updated = Datetime(
        title=u"Date update",
        description=u"Date of last update for the feed.")

    def getItems():
        """Get the individual items for the feed.

        For instance, get all announcements for a project.  Each item should
        be converted to a feed entry using itemToFeedEntry.
        """

    def getPublicRawItems():
        """Get the public items for the feed in their raw format.

        Feeds do not show private items, so this method will screen out the
        private items.
        """

    def itemToFeedEntry(item):
        """Convert a single item to a formatted feed entry.

        An individual entry will be an instance providing `IFeedEntry`.
        """

    def renderAtom():
        """Render the object as an Atom feed.

        Override this as opposed to overriding render().
        """

    def renderHTML():
        """Render the object as an html feed.

        Override this as opposed to overriding render().
        """


class IFeedEntry(Interface):
    """Interface for an entry in a feed.

    """

    title = TextLine(
        title=u"Title",
        description=u"The title of the entry")

    link_alternate = TextLine(
        title=u"Alternate URL for the entry.",
        description=u"The URL to a resource that is the human-readable "
                     "equivalent of the entry, e.g. "
                     "http://launchpad.net/ubuntu/+announcement/1")

    content = TextLine(
        title=u"Content for entry.",
        description=u"Descriptive content for the entry.  "
                     "For an announcement, for example, the content "
                     "is the text of the announcement.  It may be "
                     "plain text or formatted html, as is done for "
                     "bugs.")

class IFeedTypedData(Interface):
    """Interface for typed data in a feed."""

    content_types = List(
        title=u"Content types",
        description=u"List of supported content types",
        required=True)

    content = Text(
        title=u"Content",
        description=u"Data contents",
        required=True)


class IFeedPerson(Interface):
    """Interface for a person in a feed."""

    name = TextLine(
        title=u"Name",
        description=u"The person's name.",
        required=True)

    email = TextLine(
        title=u"Email",
        description=u"The person's email address.",
        required=False)

    uri = URI(
        title=u"URI",
        description=u"The URI for the person.",
        required=True)
