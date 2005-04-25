# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['DistroTools']

from datetime import datetime

from zope.interface import implements

from canonical.launchpad.interfaces import IDistroTools
from canonical.launchpad.database.distribution import Distribution


class DistroTools:
    """Tools for help Distribution and DistroRelase Manipulation."""

    implements(IDistroTools)

    def createDistro(self, owner, name, displayname,
                     title, summary, description, domain):
        """Create a Distribution."""
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
                                releasestatus=1,
                                sections=1,
                                lucilleconfig='')

        return release

    def getDistroReleases(self):
        return DistroRelease.select()

