# Python imports
from datetime import datetime

# Zope imports
from zope.interface import implements

# LP imports
from canonical.lp import dbschema

# interfaces and database 
from canonical.launchpad.interfaces import IDistroTools

from canonical.launchpad.database.distribution import Distribution

#
#
#

class DistroTools(object):
    """Tools for help Distribution and DistroRelase Manipulation """

    implements(IDistroTools)

    def createDistro(self, owner, name, displayname,
                     title, summary, description, domain):
        """Create a Distribution """
        ##XXX: cprov 20041207
        ## Verify the name constraint as the postgresql does.
        ## What about domain ??? 
        distro = Distribution(name=name,
                              displayname=displayname,
                              title=title,
                              summary=summary,
                              description=description,
                              domainname=domain,
                              owner=owner)

        self.createDistributionRole(distro.id, owner,
                                    dbschema.DistributionRole.DM.value)

        return distro
        

    def createDistroRelease(self, owner, title, distribution, shortdesc,
                            description, version, parent):
        ##XXX: cprov 20041207
        ## Verify the name constraint as the postgresql does.
        name = title.lower()

        ## XXX: cprov 20041207
        ## Define missed fields

        release = DistroRelease(name=name,
                                distribution=distribution,
                                title=title,
                                shortdesc=shortdesc,
                                description=description,
                                version=version,
                                owner=owner,
                                parentrelease=int(parent),
                                datereleased=datetime.utcnow(),
                                components=1,
                                releasestate=1,
                                sections=1,
                                lucilleconfig='')

        self.createDistroReleaseRole(release.id, owner,
                                     dbschema.DistroReleaseRole.RM.value)

        return release
    
    def getDistroReleases(self):
        return DistroRelease.select()
    

    def createDistributionRole(self, container_id, person, role):
        return DistributionRole(distribution=container_id,
                                personID=person, role=role)

    def createDistroReleaseRole(self, container_id, person, role):
        return DistroReleaseRole(distrorelease=container_id,
                                 personID=person, role=role)

