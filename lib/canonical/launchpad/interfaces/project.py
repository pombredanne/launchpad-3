"""Project-related Interfaces for Launchpad

(c) Canonical Ltd 2004
"""

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


class IProject(Interface):
    """A Project."""

    id = Int(title=_('ID'))
    owner = Int(title=_('Owner'))
    name = TextLine(title=_('Name'))
    displayname = TextLine(title=_('Display Name'))
    title = TextLine(title=_('Title'))
    description = Text(title=_('Description'))
    shortdesc = Text(title=_('Short Description'))
    homepageurl = TextLine(title=_('Homepage URL'))
    wikiurl = TextLine(title=_('Wiki URL'))
    lastdoap = TextLine(title=_('Last-parsed DOAP fragment'))

    def bugtrackers():
        """Return the BugTrackers for this Project."""

    def products():
        """Return Products for this Project."""

    def getProduct(name):
        """Get a product with name `name`."""
    
    def rosettaProducts():
        """Iterates over Rosetta Products in this project.
        XXX Mark Shuttleworth 02/10/04 what is the difference
            between a Rosetta Product and a normal product?
            Can this duplication be cleaned up or the difference
            clarified and documented?"""

    # XXX: This will go away once we move to project->product->potemplate
    #      traversal rather than project->potemplate traversal.
    def poTemplate(name):
        """Returns the RosettaPOTemplate with the given name."""

    def shortDescription(aDesc=None):
        """return the projects shortdesc, setting it if aDesc is provided"""

    def newSourceSource():
        """Add a SourceSource for upstream code syncing to Arch."""




# Interfaces for containers

class IProjectContainer(Interface):
    """A container for IProject objects."""

    def __getitem__(key):
        """Get a Project by name."""

    def __iter__():
        """Iterate through Projects."""

    def search(querytext):
        """Search through Projects."""

class IProjectSet(Interface):
    """The collection of projects."""

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

    def search(query):
        """Search for projects matching a certain strings."""


class IProjectBugTracker(Interface):
    id = Int(title=_('ID'))
    project = Int(title=_('Owner'))
    bugtracker = Int(title=_('Bug Tracker'))
    
