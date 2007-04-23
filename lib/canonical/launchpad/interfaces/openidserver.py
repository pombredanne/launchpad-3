# Copyright 2007 Canonical Ltd.  All rights reserved.

"""OpenId related interfaces."""

__metaclass__ = type
__all__ = [
        'IOpenIdAuthorization', 'IOpenIdAuthorizationSet',
        'ILaunchpadOpenIdStoreFactory',
        ]

from zope.schema import Int, TextLine, Datetime
from zope.interface import Interface, Attribute

class IOpenIdAuthorization(Interface):
    id = Int(title=u'ID', required=True)

    personID = Int(title=u'Person', required=True, readonly=True)
    person = Attribute('The IPerson this is for')

    client_id = TextLine(title=u'Client ID', required=False)

    date_expires = Datetime(title=u'Expiry Date', required=True)
    date_created = Datetime(
            title=u'Date Created', required=True, readonly=True
            )

    trust_root = TextLine(title=u'OpenID Trust Root', required=True)


class IOpenIdAuthorizationSet(Interface):
    def isAuthorized(person, trust_root, client_id):
        """Check the authorization list to see if the trust_root is authorized.

        Returns True or False.
        """

    def authorize(person, trust_root, expires, client_id=None):
        """Authorize the trust_root for the given person.

        If expires is None, the authorization never expires.
        
        If client_id is None, authorization is given to any client.
        If client_id is not None, authorization is only given to the client
        with the specified client_id (ie. the session cookie token).

        This method overrides any existing authorization for the given
        (person, trust_root, client_id).
        """
 
class ILaunchpadOpenIdStoreFactory(Interface):
    """Factory to create LaunchpadOpenIdStore instances."""

    def __call__():
        """Create a LaunchpadOpenIdStore instance."""

