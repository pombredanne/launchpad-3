# Copyright 2007 Canonical Ltd.  All rights reserved.

"""OpenId related interfaces."""

__metaclass__ = type
__all__ = ['IOpenIdAuthorization', 'IOpenIdAuthorizationSet']

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

