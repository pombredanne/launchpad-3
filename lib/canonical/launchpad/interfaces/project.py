"""Project-related Interfaces for Launchpad

(c) Canonical Ltd 2004
"""

from canonical.launchpad.fields import Title, Summary

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


class IProject(Interface):
    """A Project."""

    id = Int(title=_('ID'))
    owner = Int(title=_('Owner'))
    name = TextLine(title=_('Name'), description=_("""The short name of the
    project. Must be lowercase, and not contain spaces, it will be part of
    the url to this project in the Launchpad."""))
    displayname = TextLine(title=_('Display Name'), description=_("""The
        display name of the project is a short name, appropriately
        capitalised, for this product. For example, if you were referring to
        this project in a paragraph of text, you would use this name. Examples:
        the Apache Project, the Mozilla Project, the GIMP Project."""))
    title = Title(title=_('Title'), description=_("""This is the full
        title of the project, can contain spaces, special characters etc. This
        is what you would imagine seeing at the top of a page about the project.
        For example, The Apache Project, The Mozilla Project."""))
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
    

