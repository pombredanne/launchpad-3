# XXX from auth/interfaces
from zope.interface import Interface, Attribute
from persistent import IPersistent

#
# Please DO NOT put interfaces here. put them in the correct
# file, one of person, project, bug, etc.
#

from canonical.launchpad.interfaces.project import *
from canonical.launchpad.interfaces.product import *
from canonical.launchpad.interfaces.productseries import *
from canonical.launchpad.interfaces.productrelease import *
from canonical.launchpad.interfaces.sourcesource import *
from canonical.launchpad.interfaces.sourcepackage import *
from canonical.launchpad.interfaces.malone import *
from canonical.launchpad.interfaces.bug import *
from canonical.launchpad.interfaces.bugmessage import *
from canonical.launchpad.interfaces.bugactivity import *
from canonical.launchpad.interfaces.bugsubscription import *
from canonical.launchpad.interfaces.bugwatch import *
from canonical.launchpad.interfaces.bugextref import *
from canonical.launchpad.interfaces.bugattachment import *
from canonical.launchpad.interfaces.bugtracker import *
from canonical.launchpad.interfaces.bugassignment import *
from canonical.launchpad.interfaces.schema import *
from canonical.launchpad.interfaces.person import *
from canonical.launchpad.interfaces.translationeffort import *
from canonical.launchpad.interfaces.infestation import *
from canonical.launchpad.interfaces.language import *
from canonical.launchpad.interfaces.archuser import *
from canonical.launchpad.interfaces.binarypackage import *
from canonical.launchpad.interfaces.build import *
from canonical.launchpad.interfaces.distro import *
from canonical.launchpad.interfaces.gpg import *
from canonical.launchpad.interfaces.irc import *
from canonical.launchpad.interfaces.jabber import *
from canonical.launchpad.interfaces.manifest import *
from canonical.launchpad.interfaces.processor import *
from canonical.launchpad.interfaces.team import *
from canonical.launchpad.interfaces.wikiname import *
from canonical.launchpad.interfaces.pofile import *
from canonical.launchpad.interfaces.publishing import *
from canonical.launchpad.interfaces.files import *

# these will go...
from canonical.launchpad.iandrew import *
from canonical.launchpad.imark import *



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

