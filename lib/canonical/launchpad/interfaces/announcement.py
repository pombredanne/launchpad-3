# Copyright 2007 Canonical Ltd.  All rights reserved.

"""News item interfaces."""

__metaclass__ = type

__all__ = [
    'AddAnnouncementForm',
    'AnnouncementRetargetForm',
    'IAnnouncement',
    'IHasAnnouncements',
    ]

from zope.interface import Interface, Attribute
from zope.component import getUtility

from zope.schema import Datetime, Int, Choice, Text, TextLine, Bool

from canonical.launchpad import _
from canonical.launchpad.fields import AnnouncementDate, Summary, Title
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.interfaces.validation import valid_webref


class AnnouncementRetargetForm(Interface):
    """A mixin schema for an announcement.

    Requires the user to specify a project, product or distro as a target.
    """
    target = Choice(
        title=_("For"),
        description=_("The project where this announcement is being made."),
        required=True, vocabulary='DistributionOrProductOrProject')


class IHasAnnouncements(Interface):
    """A mixin class for pillars that have announcements."""

    def announce(user, title, summary=None, url=None,
                 publication_date=None):
        """Create a Announcement for this project.

        The user is the person making the announcement. The publication date
        is either 'NOW', or None (a future date), or a specified datetime.
        """

    def getAnnouncement(id):
        """Return the requested announcement."""

    def announcements(user, limit=5):
        """Return a list of announcements visible to this user.

        If limit is provided, then the list is limited to that number of the
        most recent Announcements.
        """


class AddAnnouncementForm(Interface):

    title = Title(
        title=_('Headline'), required=True)
    summary = Summary(
        title=_('Summary'), required=True)
    url = TextLine(
        title=_('URL'), required=False,
        description=_(
            "The web location of your announcement."),
        constraint=valid_webref)
    publication_date = AnnouncementDate(title=_('Date'), required=True)


class IAnnouncement(Interface):
    """A News Item."""

    # lifecycle
    id = Attribute("The unique ID of this announcement")
    date_created = Attribute("The date this announcement was registered")
    registrant = Attribute("The person who registered this announcement")
    date_announced = Attribute(
        "The date the announcement will be published, or the date it was "
        "published if it is in the past. The date will only be effective "
        "if the 'published' flag is True.")
    date_updated = Attribute(
        "The date this announcement was last updated, if ever.")

    # target
    product = Attribute("The product for this announcement.")
    project = Attribute("The project for this announcement.")
    distribution = Attribute("The distribution for this announcement.")

    target = Attribute("The pillar to which this announcement belongs.")

    # announcement details
    title = Attribute("The headline of your announcement.")
    summary = Attribute("A single-paragraph summary of the announcement.")
    url = Attribute("The web location of your announcement.")
    active = Attribute("Whether or not this announcement is published.")

    # attributes
    future = Attribute("Whether or not this announcement is yet public.")

    def modify(title, summary=None, url=None):
        """Update the details of the announcement. This will record the
        date_updated."""

    def retarget(product=None, distribution=None, project=None):
        """Retarget the announcement to a new project. One and only one of the
        arguments must not be None.
        """

    def set_publication_date(publication_date):
        """Set the publication date. The value passed is either:

          'NOW': publish this announcement immediately,
          None: publish it at some future date,
          A datetime: publish it on the date given.
        """

    def erase_permanently():
        """Remove this announcement permanently."""

