# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Interfaces for feeds generation."""

__metaclass__ = type

__all__ = [
    'IFeed',
    'IFeedPerson',
    'IFeedTypedData',
    'UnsupportedFeedFormat',
    ]

from zope.interface import Interface
from zope.schema import Datetime, Int, List, Text, TextLine, URI


class UnsupportedFeedFormat(Exception):
    """The requested feed format is not supported."""


class IFeed(Interface):
    """Interface for feeds."""

    max_age = Int(
        title=u"Maximum age",
        description=u"Maximum age in seconds for a feed to be cached.")

    quantity = Int(
        title=u"Quantity",
        description=u"Number of items to be returned in a feed.")

    title = TextLine(
        title=u"Title of the feed.")

    url = TextLine(
        title=u"URL for the feed.",
        description=u"The URL for the feed should be unique and permanent.")

    site_url = TextLine(
        title=u"Site URL",
        description=u"The URL for the main site of Launchpad.")

    feed_format = TextLine(
        title=u"Feed format",
        description=u"Requested feed format.  "
                     "Raises UnsupportedFeed if not supported.")

    logo = TextLine(
        title=u"Logo URL",
        description=u"The URL for the feed logo.")

    icon = TextLine(
        title=u"Icon URL",
        description=u"The URL for the feed icon.")

    date_updated = Datetime(
        title=u"Date update",
        description=u"Date of last update for the feed.")

    def getItems():
        """Get the individual unformatted items for the feed."""

    def getPublicRawItems():
        """Get the public items for the feed in their raw format.

        Feeds do not show private items, so this method will screen out the
        private items.
        """

    def itemToFeedEntry(item):
        """Convert a single item to a formatted feed entry."""

    def renderAtom():
        """Render the object as an Atom feed.

        Override this as opposed to overriding render().
        """

    def renderHTML():
        """Render the object as an html feed.

        Override this as opposed to overriding render().
        """


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
