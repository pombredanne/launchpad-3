"""Project-related Interfaces for Launchpad

(c) Canonical Ltd 2004
"""

from canonical.launchpad.fields import Title, Summary
from canonical.launchpad.interfaces import IRosettaStats

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


class IProject(Interface):
    """A Project."""

    id = Int(title=_('ID'), readonly=True)

    owner = Choice(title=_('Owner'), required=True, vocabulary='ValidOwner',
                   description=_("""Project owner, it can either a valid
                   Person or Team inside Launchpad context."""))
    
    name = TextLine(title=_('Name'), required=True, description=_("""The short
        name of this project, which must be unique among all the products.
        It should be at least one lowercase letters or number followed by
        one or more chars, numbers, plusses, dots or hyphens and will be
        part of the url to this project in the Launchpad."""))

    displayname = TextLine(title=_('Display Name'), description=_("""The
        display name of the project is a short name, appropriately
        capitalised, for this product. For example, if you were referring to
        this project in a paragraph of text, you would use this name. Examples:
        the Apache Project, the Mozilla Project, the GIMP Project."""))

    title = Title(title=_('Title'), description=_("""This is the full
        title of the project, can contain spaces, special characters etc.
        This is what you would imagine seeing at the top of a page about
        the project. For example, The Apache Project, The Mozilla Project."""))

    shortdesc = Summary(title=_('Project Summary'), description=_("""A summary
        of the project, in a single short paragraph."""))

    description = Text(title=_('Description'), description=_("""A couple of
        paragraphs describing the project in more detail, from the history of
        the project to current organisational structure, goals and release
        strategy."""))

    homepageurl = TextLine(title=_('Homepage URL'), description=_("""The
        project home page."""))

    wikiurl = TextLine(title=_('Wiki URL'), required=False,
                       description=_("""The URL of this project's wiki, if
                       it has one."""))

    lastdoap = TextLine(title=_('Last-parsed DOAP fragment'),
                        description=_("""The last DOAP fragment for this
                        entity that we received and parsed, or
                        generated."""),
                        required=False)

    sourceforgeproject = TextLine(title=_("SourceForge Project Name"),
                                  description=_("""The SourceForge project
                                  name for this project, if it is in
                                  sourceforge."""),
                                  required=False)

    freshmeatproject = TextLine(title=_("Freshmeat Project Name"),
                                  description=_("""The Freshmeat project
                                  name for this project, if it is in
                                  freshmeat."""),
                                required=False)

    active = Bool(title=_('Active'), required=False, description=_("""Whether
        or not this project is considered active."""))

    reviewed = Bool(title=_('Reviewed'), required=False, description=_("""Whether
        or not this project has been reviewed."""))

    def bugtrackers():
        """Return the BugTrackers for this Project."""

    def products():
        """Return Products for this Project."""

    def getProduct(name):
        """Get a product with name `name`."""

    def shortDescription(aDesc=None):
        """return the projects shortdesc, setting it if aDesc is provided"""

    def newSourceSource():
        """Add a SourceSource for upstream code syncing to Arch."""

    def product(name):
        """Return the product belonging to this project with the given
        name."""


# Interfaces for set

class IProjectSet(Interface):
    """The collection of projects."""

    title = Attribute('Title')

    def __iter__():
        """Return an iterator over all the projects."""

    def __getitem__(name):
        """Get a project by its name."""

    # XXX needs displayname, shortdesc, NO url
    def new(name, title, url, description, owner):
        """Creates a new project with the given name.

        Returns that project.

        Raises an KeyError if a project with that name already exists.
        """

    def search(text=None, soyuz=None,
                     rosetta=None, malone=None,
                     bazaar=None,
                     search_products=True):
        """Search through the DOAP database for projects that match the
        query terms. text is a piece of text in the title / summary /
        description fields of project (and possibly product). soyuz,
        bazaar, malone etc are hints as to whether the search should
        be limited to projects that are active in those Launchpad
        applications."""

    def forReview():
        """Return a list of Projects which need review, or which have
        products that needs review."""

    def forSyncReview():
        """Return a list of projects that have sourcesources which need
        review."""

class IProjectBugTracker(Interface):
    id = Int(title=_('ID'))
    project = Int(title=_('Owner'))
    bugtracker = Int(title=_('Bug Tracker'))

