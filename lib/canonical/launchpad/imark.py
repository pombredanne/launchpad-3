
# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.interface import implements, Interface, Attribute


__all__ = ['IDOAPApplication', 'IProjectContainer', 'IFOAFApplication', 'IProjectContainer']

class IEmailAddress(Interface):
    id = Int(
        title=_('ID'), required=True, readonly=True,
        )
    email = Text(
        title=_('Email Address'), required=True,
        )
    status = Int(
        title=_('Status'), required=True,
        )
    person = Int(
        title=_('Person'), required=True,
        )
    
class IPerson(Interface):
    """A Person."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    displayname = TextLine(
            title=_('Display Name'), required=False, readonly=False,
            )
    givenname = TextLine(
            title=_('Given Name'), required=False, readonly=False,
            )
    familyname = TextLine(
            title=_('Family Name'), required=False, readonly=False,
            )
    password = Password(
            title=_('Password'), required=False, readonly=False,
            )
    teamowner = Int(
            title=_('Team Owner'), required=False, readonly=False,
            )
    teamdescription = TextLine(
            title=_('Team Description'), required=False, readonly=False,
            )
    # TODO: This should be required in the DB, defaulting to something
    karma = Int(
            title=_('Karma'), required=False, readonly=True,
            )
    # TODO: This should be required in the DB, defaulting to something
    karmatimestamp = Datetime(
            title=_('Karma Timestamp'), required=False, readonly=True,
            )

class IDOAPApplication(Interface):
    """DOAP application class."""

# Interfaces for containers

class IProjectContainer(Interface):
    """A container for IProject objects."""

    def __getitem__(key):
        """Get a Project by name."""

    def __iter__():
        """Iterate through Projects."""

    def search(querytext):
        """Search through Projects."""


class IFOAFApplication(Interface):
    """FOAF application class."""

# Interfaces for containers

class IProjectContainer(Interface):
    """A container for IProject objects."""

    def __getitem__(key):
        """Get a Project by name."""

    def __iter__():
        """Iterate through Projects."""

    def search(querytext):
        """Search through Projects."""

class IProject(Interface):
    """A Project."""

    id = Int(title=_('ID'))
    owner = Int(title=_('Owner'))
    name = TextLine(title=_('Name'))
    title = TextLine(title=_('Title'))
    description = Text(title=_('Description'))
    shortdesc = Text(title=_('Short Description'))
    homepageurl = TextLine(title=_('Homepage URL'))

    def displayName(aDesc=None):
        """return the projects shortdesc, setting it if aDesc is provided"""

    def products():
        """Return Products for this Project."""

    def getProduct(name):
        """Get a product with name `name`."""
    
    def rosettaProducts():
        """Iterates over RosettaProducts in this project."""

    # XXX: This will go away once we move to project->product->potemplate
    #      traversal rather than project->potemplate traversal.
    def poTemplate(name):
        """Returns the RosettaPOTemplate with the given name."""

    def shortDescription(aDesc=None):
        """return the projects shortdesc, setting it if aDesc is provided"""



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


class IProduct(Interface):
    """A Product."""

    project = Int(title=_('Project'))
    owner = Int(title=_('Owner'))
    name = TextLine(title=_('Name'))
    title = TextLine(title=_('Title'))
    shortdesc = Text(title=_('Short description'))
    description = Text(title=_('Description'))
    homepageurl = TextLine(title=_('Homepage URL'))
    manifest = TextLine(title=_('Manifest'))
    syncs = Attribute(_('Sync jobs'))

    def bugs():
        """Return ProductBugAssignments for this Product."""

