# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Project-related interfaces for Launchpad."""

__metaclass__ = type

__all__ = [
    'IProject',
    'IProjectSet',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Bool, Choice, Int, Text, TextLine

from canonical.launchpad import _
from canonical.launchpad.fields import Summary, Title, URIField
from canonical.launchpad.interfaces.branchvisibilitypolicy import (
    IHasBranchVisibilityPolicy)
from canonical.launchpad.interfaces.bugtarget import IBugTarget
from canonical.launchpad.interfaces.karma import IKarmaContext
from canonical.launchpad.interfaces.launchpad import (
    IHasAppointedDriver, IHasIcon, IHasLogo, IHasMugshot, IHasOwner)
from canonical.launchpad.interfaces.mentoringoffer import IHasMentoringOffers
from canonical.launchpad.interfaces.milestone import IHasMilestones
from canonical.launchpad.interfaces.announcement import IMakesAnnouncements
from canonical.launchpad.interfaces.pillar import PillarNameField
from canonical.launchpad.interfaces.specificationtarget import (
    IHasSpecifications)
from canonical.launchpad.interfaces.sprint import IHasSprints
from canonical.launchpad.interfaces.translationgroup import (
    IHasTranslationGroup)
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.fields import (
    IconImageUpload, LogoImageUpload, MugshotImageUpload)


class ProjectNameField(PillarNameField):

    @property
    def _content_iface(self):
        return IProject


class IProject(IBugTarget, IHasAppointedDriver, IHasBranchVisibilityPolicy,
               IHasIcon, IHasLogo, IHasMentoringOffers, IHasMilestones,
               IHasMugshot, IHasOwner, IHasSpecifications,
               IHasSprints, IHasTranslationGroup, IMakesAnnouncements,
               IKarmaContext):
    """A Project."""

    id = Int(title=_('ID'), readonly=True)

    owner = Choice(
        title=_('Owner'),
        required=True,
        vocabulary='ValidOwner',
        description=_("""Project group owner, it can either a valid
            Person or Team inside Launchpad context."""))

    name = ProjectNameField(
        title=_('Name'),
        required=True,
        description=_("""A unique name, used in URLs, identifying the project
            group.  All lowercase, no special characters.
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
        description=_("""The full name of the project group,
            which can contain spaces, special characters etc."""))

    summary = Summary(
        title=_('Project Group Summary'),
        description=_("""A brief (one-paragraph) summary of the project group."""))

    description = Text(
        title=_('Description'),
        description=_("""A detailed description of the project group,
            including details like when it was founded,
            how many contributors there are,
            and how it is organised and coordinated."""))

    datecreated = TextLine(
        title=_('Date Created'),
        description=_("""The date this project group was created in Launchpad."""))

    driver = Choice(
        title=_("Driver"),
        description=_(
            "This is a project group-wide appointment, think carefully here! "
            "This person or team will be able to set feature goals and "
            "approve bug targeting and backporting for ANY series in "
            "ANY project in this group. You can also appoint drivers "
            "at the level of a specific project or series. So you may "
            "just want to leave this space blank, and instead let the "
            "individual projects and series have drivers."),
        required=False, vocabulary='ValidPersonOrTeam')

    drivers = Attribute("A list of drivers, to make Object.drivers a "
        "standard pattern of access.")

    homepageurl = URIField(
        title=_('Homepage URL'),
        required=False,
        allowed_schemes=['http', 'https', 'ftp'], allow_userinfo=False,
        description=_("""The project group home page. Please include the http://"""))

    wikiurl = URIField(
        title=_('Wiki URL'),
        required=False,
        allowed_schemes=['http', 'https', 'ftp'], allow_userinfo=False,
        description=_("""The URL of this project group's wiki, if it has one.
            Please include the http://"""))

    lastdoap = TextLine(
        title=_('Last-parsed RDF fragment'),
        description=_("""The last RDF fragment for this
           entity that we received and parsed, or
           generated."""),
        required=False)

    sourceforgeproject = TextLine(
        title=_("SourceForge Project Name"),
        description=_("""The SourceForge project name for this project group,
            if it is in sourceforge."""),
        required=False)

    freshmeatproject = TextLine(
        title=_("Freshmeat Project Name"),
        description=_("""The Freshmeat project name for this project group,
            if it is in freshmeat."""),
        required=False)

    homepage_content = Text(
        title=_("Homepage Content"), required=False,
        description=_(
            "The content of this project group's home page. Edit this and it "
            "will be displayed for all the world to see. It is NOT a wiki "
            "so you cannot undo changes."))

    icon = IconImageUpload(
        title=_("Icon"), required=False,
        default_image_resource='/@@/project',
        description=_(
            "A small image of exactly 14x14 pixels and at most 5kb in size, "
            "that can be used to identify this project group. The icon will be "
            "displayed in Launchpad everywhere that we link to this "
            "project group. For example in listings or tables of active "
	    "project groups."))

    logo = LogoImageUpload(
        title=_("Logo"), required=False,
        default_image_resource='/@@/project-logo',
        description=_(
            "An image of exactly 64x64 pixels that will be displayed in "
            "the heading of all pages related to this project group. It should "
            "be no bigger than 50kb in size."))

    mugshot = MugshotImageUpload(
        title=_("Brand"), required=False,
        default_image_resource='/@@/project-mugshot',
        description=_(
            "A large image of exactly 192x192 pixels, that will be displayed "
            "on this project group's home page in Launchpad. It should be no "
            "bigger than 100kb in size. "))

    active = Bool(title=_('Active'), required=False,
        description=_(
	    "Whether or not this project group is considered active."))

    reviewed = Bool(title=_('Reviewed'), required=False,
        description=_("Whether or not this project group has been reviewed."))

    bounties = Attribute(
        _("The bounties that are related to this project group."))

    bugtracker = Choice(title=_('Bug Tracker'), required=False,
        vocabulary='BugTracker',
        description=_(
	    "The bug tracker the products in this project group use."))

    products = Attribute(
        _("An iterator over the active Products for this project group."))

    def getProduct(name):
        """Get a product with name `name`."""

    def ensureRelatedBounty(bounty):
        """Ensure that the bounty is linked to this project group. Return None.
        """

    def translatables():
        """Return an iterator over products that have resources translatables.

        It also should have IProduct.official_rosetta flag set.
        """

    def hasProducts():
        """Returns True if a project has products associated with it, False
        otherwise.
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

    def new(name, displayname, title, homepageurl, summary, description,
            owner, mugshot=None, logo=None, icon=None):
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
