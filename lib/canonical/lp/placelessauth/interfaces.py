from zope.app.security.interfaces import IAuthenticationService, IPrincipal
from zope.app.pluggableauth.interfaces import IPrincipalSource
from zope.interface import Interface

class IPlacelessAuthUtility(IAuthenticationService):
    """ This is a marker interface for a utility that supplies the interface
    of the authentication service placelessly, with the addition of
    a method to allow the acquisition of a principal using his
    login name """
    def getPrincipalByLogin(login):
        """ Return a principal based on his login name  """

class IPlacelessLoginSource(IPrincipalSource):
    """ This is a principal source that has no place.  It extends
    the pluggable auth IPrincipalSource interface, allowing for disparity
    between the user id and login name """
    def getPrincipalByLogin(login):
        """ Return a principal based on his login name """

class IPasswordEncryptor(Interface):
    """ An interface representing a password encryption scheme """
    def encrypt(plaintext):
        """
        Return the encrypted value of plaintext.
        """
        
    def validate(plaintext, encrypted):
        """
        Return a true value if the encrypted value of 'plaintext' is
        equivalent to the value of 'encrypted'.  In general, if this
        method returns true, it can also be assumed that the value of
        self.encrypt(plaintext) will compare equal to 'encrypted'.
        """
  
class ILaunchpadPrincipal(IPrincipal):
    """Placeholder interface"""

