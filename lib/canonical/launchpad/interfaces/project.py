# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Project-related interfaces for Launchpad."""

__metaclass__ = type

__all__ = [
    'IProject',
    'IProjectSet',
    'IProjectBugTracker',
    'IProjectBugTrackerSet',
    ]

from canonical.launchpad.fields import Title, Summary
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.interfaces.launchpad import IHasOwner

from zope.schema import Bool, Choice, Int, Text, TextLine
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')


class IProject(IHasOwner):
    """A Project."""

    id = Int(title=_('ID'), readonly=True)

    owner = Choice(
        title=_('Owner'),
        required=True,
        vocabulary='ValidOwner',
        description=_("""Project owner, it can either a valid
            Person or Team inside Launchpad context."""))

    name = TextLine(
        title=_('Name'),
        required=True,
        description=_("""The short
            name of this project, which must be unique among all the products.
            It should be at least one lowercase letters or number followed by
            one or more chars, numbers, plusses, dots or hyphens and will be
            part of the url to this project in the Launchpad."""),
        constraint=valid_name)

    displayname = TextLine(
        title=_('Display Name'),
        description=_("""The display name of the project is a short name,
            appropriately capitalised, for this product. For example,
            if you were referring to this project in a paragraph of text,
            you would use this name. Examples: the Apache Project, the
            Mozilla Project, the GIMP Project."""))

    title = Title(
        title=_('Title'),
        description=_("""This is the full title of the project, can contain
            spaces, special characters etc.  This is what you would imagine
            seeing at the top of a page about the project. For example,
            The Apache Project, The Mozilla Project."""))

    summary = Summary(
        title=_('Project Summary'),
        description=_("""A summary of the project, in a single
            short paragraph."""))

    description = Text(
        title=_('Description'),
        description=_("""A couple of paragraphs describing the project
            in more detail, from the history of the project to current
            organisational structure, goals and release strategy."""))

    datecreated = TextLine(
        title=_('Date Created'),
        description=_("""The date this project was created in Launchpad."""))

    homepageurl = TextLine(
        title=_('Homepage URL'),
        description=_("""The project home page. Please include the http://"""))

    wikiurl = TextLine(
        title=_('Wiki URL'),
        required=False,
        description=_("""The URL of this project's wiki, if it has one.
            Please include the http://"""))

    lastdoap = TextLine(
        title=_('Last-parsed RDF fragment'),
        description=_("""The last RDF fragment for this
           entity that we received and parsed, or
           generated."""),
        required=False)

    sourceforgeproject = TextLine(
        title=_("SourceForge Project Name"),
        description=_("""The SourceForge project name for this project,
            if it is in sourceforge."""),
        required=False)

    freshmeatproject = TextLine(
        title=_("Freshmeat Project Name"),
        description=_("""The Freshmeat project name for this project,
            if it is in freshmeat."""),
        required=False)

    translationgroup = Choice(
        title = _("Translation group"),
        description = _("The translation group for this product. This group "
            "is made up of a set of translators for all the languages "
            "approved by the group manager. These translators then have "
            "permission to edit the groups translation files, based on the "
            "permission system selected below."),
        required=False,
        vocabulary='TranslationGroup')

    translationpermission = Choice(
        title=_("Translation Permission System"),
        description=_("The permissions this group requires for "
            "translators. If 'Open', then anybody can edit translations "
            "in any language. If 'Reviewed', then anybody can make "
            "suggestions but only the designated translators can edit "
            "or confirm translations. And if 'Closed' then only the "
            "designated translation group will be able to touch the "
            "translation files at all."),
        required=True,
        vocabulary='TranslationPermission')

    active = Bool(title=_('Active'), required=False,
        description=_("Whether or not this project is considered active."))

    reviewed = Bool(title=_('Reviewed'), required=False,
        description=_("Whether or not this project has been reviewed."))

    bounties = Attribute(_("The bounties that are related to this project."))

    def bugtrackers():
        """Return the BugTrackers for this Project."""

    def products():
        """Return Products for this Project."""

    def getProduct(name):
        """Get a product with name `name`."""

    def shortDescription(aDesc=None):
        """return the projects summary, setting it if aDesc is provided"""

    def product(name):
        """Return the product belonging to this project with the given
        name."""

    def ensureRelatedBounty(bounty):
        """Ensure that the bounty is linked to this project. Return None.
        """


# Interfaces for set

class IProjectSet(Interface):
    """The collection of projects."""

    title = Attribute('Title')

    def __iter__():
        """Return an iterator over all the projects."""

    def __getitem__(name):
        """Get a project by its name."""

    # XXX needs displayname, summary, NO url
    def new(name, title, url, description, owner):
        """Creates a new project with the given name.

        Returns that project.

        Raises an KeyError if a project with that name already exists.
        """

    def search(text=None, soyuz=None,
                     rosetta=None, malone=None,
                     bazaar=None,
                     search_products=True):
        """Search through the Registry database for projects that match the
        query terms. text is a piece of text in the title / summary /
        description fields of project (and possibly product). soyuz,
        bazaar, malone etc are hints as to whether the search should
        be limited to projects that are active in those Launchpad
        applications."""

    def forReview():
        """Return a list of Projects which need review, or which have
        products that needs review."""

    def forSyncReview():
        """Return a list of projects that have productseries ready to
        import which need review."""

class IProjectBugTracker(Interface):
    id = Int(title=_('ID'))
    project = Int(title=_('Owner'))
    bugtracker = Int(title=_('Bug Tracker'))

class IProjectBugTrackerSet(Interface):
    def new(project, bugtracker):
        """Create a new project bug tracker."""

