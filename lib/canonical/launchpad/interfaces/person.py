# Imports from zope
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

class IPerson(Interface):
    """A Person."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    name = TextLine(
            title=_('Unique Launchpad Name'), required=False, readonly=False,
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
    languages = Attribute(_('List of know languages by this person'))

    def browsername():
        """Return a textual name suitable for display in a browser."""

    def addLanguage(language):
        """Adds a new language to the list of know languages."""

    def removeLanguage(language):
        """Removed the language from the list of know languages."""


class IPersonSet(Interface):
    """The set of Persons."""

    def __getitem__(personid):
        """Returns the person with the given id.

        Raises KeyError if there is no such person.
        """

    def get(personid, default=None):
        """Returns the person with the given id.

        Returns the default value if there is no such person.
        """

    def getByEmail(email, default=None):
        """Returns the person with the given email address.

        Returns the default value if there is no such person.
        """
    
    def getAll():
        """Returns all People in a database"""

class IEmailAddress(Interface):
    """The object that stores the IPerson's emails."""
    # XXX Mark Shuttleworth 08/10/04
    #     commented out to see if it breaks anything, i'd prefer not to
    #     expose id's unless required. If it hasn't broken anything, plese
    #     remove after 16/20/04
    #id = Int(
    #    title=_('ID'), required=True, readonly=True,
    #    )
    email = Text(
        title=_('Email Address'), required=True,
        )
    status = Int(
        title=_('Email Address Status'), required=True,
        )
    person = Int(
        title=_('Person'), required=True,
        )
    statusname = Attribute("StatusName")


#
# Person related Applications Interfaces
#

class IPeopleApp(Interface):
    """A People Tag """
    p_entries = Attribute("Number of person entries")
    t_entries = Attribute("Number of teams entries")

    def __getitem__(release):
        """retrieve personal by name"""

    def __iter__():
        """retrieve an iterator"""


class IPersonApp(Interface):
    """A Person Tag """
    person = Attribute("Person entry")
    id = Attribute("Person entry")
    email = Attribute("Email")
    wiki = Attribute("Wiki")
    jabber = Attribute("Jabber")
    irc = Attribute("IRC")    
    archuser = Attribute("Arch user")    
    gpg = Attribute("GPG")

    members = Attribute("Members of a Team")
    teams = Attribute("Team which I'm a member")
    subteams = Attribute("Sub Teams")
    distroroles = Attribute("Distribution Roles")
    distroreleaseroles = Attribute("Distrorelase Roles")

    packages = Attribute("A Selection of SourcePackageReleases")

    roleset = Attribute("Possible Roles")
    statusset = Attribute("Possible Status")

