# Copyright 2004 Canonical Ltd.  All rights reserved.

"""Karma interfaces."""

__metaclass__ = type

__all__ = [
    'IKarma',
    'IKarmaSet',
    'IKarmaAction',
    'IKarmaActionSet',
    'IKarmaCache',
    'IKarmaCacheSet',
    'IKarmaCategory',
    ]

from zope.app.form.browser.interfaces import IAddFormCustomization
from zope.schema import Int, Datetime, Choice, Text, TextLine
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class IKarma(Interface):
    """The Karma of a Person."""

    title = Attribute('Title')

    id = Int(title=_("Database ID"), required=True, readonly=True)

    person = Int(
        title=_("Person"), required=True, readonly=True,
        description=_("The user which this karma is assigned to."))

    action = Int(
        title=_("Action"), required=True,
        description=_("The action which gives the karma to the user."))

    datecreated = Datetime(
        title=_("Date Created"), required=True, readonly=True,
        description=_("The date this karma was assigned to the user."))


class IKarmaSet(Interface):
    """The set of Karma objects."""

    def selectByPersonAndAction(person, action):
        """Return all Karma objects for the given person and action."""

    def getSumByPerson(person):
        """Return the sum of all karma points of <person>.

        This sum is obtained through the following equation:
        s = s1 + (s2 * 0.5) + (s3 * 0.2)
        Where, 
        s1: Sum of all karma assigned during the last 30 days
        s2: Sum of all karma assigned between 90 days ago and 30 days ago
        s3: Sum of all karma assigned prior to 90 days ago
        """

    def getSumByPersonAndCategory(person, category):
        """Return the sum of karma points given to <person> for actions of the
        given category that s(he) performed.

        This sum is obtained through the following equation:
        s = s1 + (s2 * 0.5) + (s3 * 0.2)
        Where, 
        s1: Sum of all karma assigned during the last 30 days
        s2: Sum of all karma assigned between 90 days ago and 30 days ago
        s3: Sum of all karma assigned prior to 90 days ago
        """


class IKarmaAction(Interface):
    """The Action that gives karma to a Person."""

    #id = Int(title=_("Database ID"), required=True, readonly=True)
    name = TextLine(
        title=_("Name"), required=True, readonly=True)
    category = Choice(
        title=_("Category"), required=True, readonly=False,
        vocabulary='KarmaCategory')
    title = TextLine(title=_("Title"), required=True)
    summary = Text(title=_("Summary"), required=True)
    points = Int(
        title=_("Points"), required=True, readonly=False,
        description=_("The number of points we give to a user which performs "
                      "this action."))


class IKarmaActionSet(IAddFormCustomization):
    """The set of actions that gives karma to a Person."""

    title = Attribute('Title')

    def getByName(name, default=None):
        """Return the KarmaAction with the given name.

        Return the default value if there's no such KarmaAction.
        """

    def selectByCategory(category):
        """Return all KarmaAction objects of the given category."""

    def selectByCategoryAndPerson(category, person, orderBy=None):
        """Return all KarmaAction objects of the given category if <person>
        performed these actions at least once.

        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        If no orderBy is specified the results will be ordered using the
        default ordering specified in KarmaAction._defaultOrder.
        """


class IKarmaCache(Interface):
    """A cached value of a person's karma."""

    title = Attribute('Title')

    id = Int(title=_("Database ID"), required=True, readonly=True)

    person = Int(
        title=_("Person"), required=True, readonly=True,
        description=_("The person which performed the actions of this "
                      "category, and thus got the karma."))

    category = Choice(
        title=_("Category"), required=True, readonly=True,
        vocabulary='KarmaCategory')

    karmavalue = Int(
        title=_("Karma"), required=True, readonly=False,
        description=_("The karma points of all actions of this category "
                      "performed by this person."))


class IKarmaCacheSet(Interface):
    """The set of KarmaCache."""

    title = Attribute('Title')

    def getByPersonAndCategory(person, category, default=None):
        """Return the KarmaCache for <person> of the given category.

        Return the default value if there's no KarmaCache for <person> and
        <category>.
        """

    def new(person, category, karmavalue):
        """Create a KarmaCache for <person> with <category> and <karmavalue>.

        Return the newly created KarmaCache.
        """


class IKarmaCategory(Interface):
    """A catgory of karma events."""

    name = Attribute("The name of the category.")
    title = Attribute("The title of the karma category.")
    summary = Attribute("A brief summary of this karma category.")


