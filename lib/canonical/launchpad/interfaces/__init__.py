from canonical.launchpad.iandrew import *
from canonical.launchpad.imark import *
from canonical.launchpad.ikiko import *
from canonical.launchpad.isteve import *
from canonical.launchpad.icelso import *

# XXX from auth/interfaces
from zope.interface import Interface, Attribute
from persistent import IPersistent

#
# Please DO NOT put interfaces here. put them in the correct
# file, one of person, project, bug, etc.
#

from canonical.launchpad.interfaces.project import *

class IAuthApplication(Interface):
    """ Interface for AuthApplication """
    def __getitem__(name):
        """ The __getitem__ method used to traversing """

class IPasswordResets(IPersistent):
    """Interface for PasswordResets"""

    lifetime = Attribute("Maximum time between request and reset password")
    
    def newURL(person):
        """Create a new URL and store person and creation time"""
        
        
    def getPerson(long_url):
        """Get the person object using the long_url if not expired"""

class IPasswordChangeApp(Interface):
    """Interface for PasswdChangeApp."""
    code = Attribute("The transaction code")

class IPersonSet(Interface):
    """The set of Persons."""

    def __getitem__(personid):
        """Returns the person with the given id.

	Raises KeyError if there is no such person.
	"""
