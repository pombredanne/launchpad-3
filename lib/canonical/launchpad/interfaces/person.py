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
            title=_('Unique Launchpad Name'), required=True, readonly=False,
            )
    displayname = TextLine(
            title=_('Display Name'), required=True, readonly=False,
            )
    givenname = TextLine(
            title=_('Given Name'), required=False, readonly=False,
            )
    familyname = TextLine(
            title=_('Family Name'), required=False, readonly=False,
            )
    password = Password(
            title=_('Password'), required=True, readonly=False,
            )
    teamowner = Int(
            title=_('Team Owner'), required=False, readonly=False,
            )
    teamdescription = Text(
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
    sshkeys = Attribute(_('List of SSH keys'))

    # XXX: These fields are used only to generate the form to create a
    # new person.
    email = TextLine(title=_('Email'), required=True)
    password2 = Password(title=_('Retype Password'), required=True)

    # Properties of the Person object.
    gpg = Attribute("GPG")
    irc = Attribute("IRC")    
    bugs = Attribute("Bug")
    wiki = Attribute("Wiki")
    teams = Attribute("Team which I'm a member")
    emails = Attribute("Email")
    jabber = Attribute("Jabber")
    roleset = Attribute("Possible Roles")
    members = Attribute("Members of a Team")
    archuser = Attribute("Arch user")    
    subteams = Attribute("Sub Teams")
    packages = Attribute("A Selection of SourcePackageReleases")
    statusset = Attribute("Possible Status")
    activities = Attribute("Karma")
    distroroles = Attribute("Distribution Roles")
    translations = Attribute("Translations")
    distroreleaseroles = Attribute("Distrorelase Roles")

    def browsername():
        """Return a textual name suitable for display in a browser."""

    def addLanguage(language):
        """Adds a new language to the list of know languages."""

    def removeLanguage(language):
        """Removed the language from the list of know languages."""

    def inTeam(team_name):
        """Return true if this person is in the named team."""


class ITeam(Interface):
    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    name = TextLine(
            title=_('Unique Launchpad Name'), required=True, readonly=False,
            )
    displayname = TextLine(
            title=_('Display Name'), required=True, readonly=False,
            )
    teamowner = Int(
            title=_('Team Owner'), required=False, readonly=False,
            )
    teamdescription = Text(
            title=_('Team Description'), required=False, readonly=False,
            )
    # XXX: salgado: As soon as we manage a way to generate a nickname
    # without an email address, this shouldn't be required anymore.
    email = TextLine(title=_('Email'), required=True)


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
    
    def getByName(name):
        """Returns the person with the given name.
        """
    
    def getAll():
        """Returns all People in a database"""

    def getContributorsForPOFile(pofile):
        """Returns the list of persons that have an active contribution for a
        concrete POFile."""


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

