
#
# This implements the IFoaf Utility, which is a sort of swiss-army-knife
# toolkit of foaf-related functions.
#

from zope.interface import implements
from zope.component import getUtility

from canonical.launchpad.interfaces import IFoaf, IPerson, \
        IPersonSet

from canonical.launchpad.database import Person, EmailAddress

class Foaf:

    implements(IFoaf)

    def __init__(self):
        self.people = getUtility(IPersonSet)
        self.emails = getUtility(IEmailAddressSet)

    def getPersonByName(self, name):
        return self.people.get(name=name)

    def getPersonByEmail(self, email):
        return self.people.get(email=email)

