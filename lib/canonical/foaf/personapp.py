"""Person App Components for Foaf.

(c) Canonical Software Ltd. 2004, all rights reserved.
"""

# Zope imports
from zope.interface import implements
from zope.component import getUtility

# sqlos and SQLObject imports
from canonical.lp import dbschema

# Launchpad imports
from canonical.launchpad.database import Person, \
                                         EmailAddress, GPGKey, \
                                         ArchUserID, WikiName, JabberID, \
                                         IrcID, Membership, TeamParticipation,\
                                         DistributionRole, DistroReleaseRole

from canonical.launchpad.interfaces import IPeopleApp, IPersonApp, \
                                           ISourcePackageSet, \
                                           ITeamParticipationSet


#
# 
#

class PeopleApp(object):
    implements(IPeopleApp)
    
    def __init__(self):
        # FIXME: (tmp_names) Daniel Debonzi - 2004-10-13
        # these names are totaly crap
        self.p_entries = Person.select('teamowner IS NULL').count()
        self.t_entries = Person.select('teamowner IS NOT NULL').count()

    def __getitem__(self, name):
        try:
            return PersonApp(name)
        except Exception, e:
            print e.__class__, e
            raise

    def __iter__(self):
        return iter(Person.select(orderBy='displayname'))

class PersonApp(object):
    implements(IPersonApp)

    def __init__(self, name):
        self.person = Person.selectBy(name=name)[0]
        self.id = self.person.id
        
        self.packages = self._getSourcesByPerson()

        self.roleset = []
        self.statusset = []


        # FIXME: (dbschema_membershiprole) Daniel Debonzi
        # 2004-10-13
        # Crap solution for <select> entity on person-join.pt
        for item in dbschema.MembershipRole.items:
            self.roleset.append(item.title)
        for item in dbschema.MembershipStatus.items:
            self.statusset.append(item.title)

        
        # FIXME: Daniel Debonzi 2004-10-13
        # Most of this code probably belongs as methods/properties of
        # Person

        try:
            self.members = Membership.selectBy(teamID=self.id)
            if self.members.count() == 0:
                self.members = None                
        except IndexError:
            self.members = None

        try:
            # FIXME: (my_team) Daniel Debonzi 2004-10-13
            # My Teams should be:
            # -> the Teams owned by me
            # OR
            # -> the Teams which I'm member (as It is)
            self.teams = TeamParticipation.selectBy(personID=self.id)
            if self.teams.count() == 0:
                self.teams = None                
        except IndexError:
            self.teams = None

        teampart = getUtility(ITeamParticipationSet)
        try:
            self.subteams = teampart.getSubTeams(self.id)
            
            if self.subteams.count() == 0:
                self.subteams = None                
        except IndexError:
            self.subteams = None

        try:
            self.distroroles = DistributionRole.selectBy(personID=self.id)
            if self.distroroles.count() == 0:
                self.distroroles = None
                
        except IndexError:
            self.distroroles = None

        try:
            self.distroreleaseroles = DistroReleaseRole.selectBy(personID=\
                                                                 self.id)
            if self.distroreleaseroles.count() == 0:
                self.distroreleaseroles = None
        except IndexError:
            self.distroreleaseroles = None
            
        # Retrieve an email by person id
        
        self.email = EmailAddress.selectBy(personID=self.id)

        try:
            self.wiki = WikiName.selectBy(personID=self.id)[0]
        except IndexError:
            self.wiki = None
        try:
            self.jabber = JabberID.selectBy(personID=self.id)[0]
        except IndexError:
            self.jabber = None
        try:
            self.archuser = ArchUserID.selectBy(personID=self.id)[0]
        except IndexError:
            self.archuser = None
        try:
            self.irc = IrcID.selectBy(personID=self.id)[0]
        except IndexError:
            self.irc = None
        try:
            self.gpg = GPGKey.selectBy(personID=self.id)[0]
        except IndexError:
            self.gpg = None

    def _getSourcesByPerson(self):
        sputil = getUtility(ISourcePackageSet)
        return sputil.getByPersonID(self.id)
    

