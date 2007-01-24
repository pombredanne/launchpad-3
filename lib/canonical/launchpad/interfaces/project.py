# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Project-related interfaces for Launchpad."""

__metaclass__ = type

__all__ = [
    'IProject',
    'IProjectSet',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Bool, Bytes, Choice, Int, Text, TextLine

from canonical.launchpad import _
from canonical.launchpad.fields import Summary, Title
from canonical.launchpad.interfaces import (
        IHasOwner, IBugTarget, IHasSpecifications, PillarNameField,
        valid_emblem, valid_gotchi, valid_webref)
from canonical.launchpad.validators.name import name_validator


class ProjectNameField(PillarNameField):

    @property
    def _content_iface(self):
        return IProject


class IProject(IHasOwner, IBugTarget, IHasSpecifications):
    """A Project."""

    id = Int(title=_('ID'), readonly=True)

    owner = Choice(
        title=_('Owner'),
        required=True,
        vocabulary='ValidOwner',
        description=_("""Project owner, it can either a valid
            Person or Team inside Launchpad context."""))

    name = ProjectNameField(
        title=_('Name'),
        required=True,
        description=_("""A unique name, used in URLs, identifying the project.
            All lowercase, no special characters.
            Examples: apache, mozilla, gimp."""),
        constraint=name_validator)

    displayname = TextLine(
        title=_('Display Name'),
        description=_("""Appropriately capitalised,
            and typically ending in "Project".
            Examples: the Apache Project, the Mozilla Project,
            the Gimp Project."""))

    title = Title(
        title=_('Title'),
        description=_("""The full name of the project,
            which can contain spaces, special characters etc."""))

    summary = Summary(
        title=_('Project Summary'),
        description=_("""A brief (one-paragraph) summary of the project."""))

    description = Text(
        title=_('Description'),
        description=_("""A detailed description of the project,
            including details like when it was founded, 
            how many contributors there are,
            and how it is organised and coordinated."""))

    datecreated = TextLine(
        title=_('Date Created'),
        description=_("""The date this project was created in Launchpad."""))

    driver = Choice(
        title=_("Driver"),
        description=_(
            "This is a project-wide appointment, think carefully here! "
            "This person or team will be able to set feature goals and "
            "approve bug targeting and backporting for ANY series in "
            "ANY product in this project. You can also appoint drivers "
            "at the level of a specific product or series. So you may "
            "just want to leave this space blank, and instead let the "
            "individual products and series have drivers."),
        required=False, vocabulary='ValidPersonOrTeam')

    homepageurl = TextLine(
        title=_('Homepage URL'),
        required=False,
        constraint=valid_webref,
        description=_("""The project home page. Please include the http://"""))

    wikiurl = TextLine(
        title=_('Wiki URL'),
        required=False,
        constraint=valid_webref,
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

    homepage_content = Text(
        title=_("Homepage Content"), required=False,
        description=_(
            "The content of this project's home page. Edit this and it will "
            "be displayed for all the world to see. It is NOT a wiki "
            "so you cannot undo changes."))

    emblem = Bytes(
        title=_("Emblem"), required=False,
        description=_(
            "A small image, max 16x16 pixels and 8k in file size, that can "
            "be used to refer to this project."),
        constraint=valid_emblem)

    gotchi = Bytes(
        title=_("Gotchi"), required=False,
        description=_(
            "An image, maximum 150x150 pixels, that will be displayed on "
            "this project's home page. It should be no bigger than 50k in "
            "size. "),
        constraint=valid_gotchi)

    translationgroup = Choice(
        title = _("Translation group"),
        description = _("The translation group for this project. This group "
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

    bugtracker = Choice(title=_('Bug Tracker'), required=False,
        vocabulary='BugTracker',
        description=_("The bug tracker the products in this project use."))

    products = Attribute(_("An iterator over the Products for this project."))

    def getProduct(name):
        """Get a product with name `name`."""

    def ensureRelatedBounty(bounty):
        """Ensure that the bounty is linked to this project. Return None.
        """

    def translatables():
        """Return an iterator over products that have resources translatables.

        It also should have IProduct.official_rosetta flag set.
        """


# Interfaces for set

class IProjectSet(Interface):
    """The collection of projects."""

    title = Attribute('Title')

    def __iter__():
        """Return an iterator over all the projects."""

    def __getitem__(name):
        """Get a project by its name."""

    def get(projectid):
        """Get a project by its id.

        If the project can't be found a NotFoundError will be raised.
        """

    def getByName(name, default=None, ignore_inactive=False):
        """Return the project with the given name, ignoring inactive projects
        if ignore_inactive is True.
        
        Return the default value if there is no such project.
        """

    def new(name, displayname, title, homepageurl, summary, description, owner):
        """Create and return a project with the given arguments."""

    def count_all():
        """Return the total number of projects registered in Launchpad."""

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
