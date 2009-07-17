# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""OpenID related interfaces."""

__metaclass__ = type
__all__ = [
    'IOpenIDApplication',
    'IOpenIDAuthorization',
    'IOpenIDAuthorizationSet',
    'IOpenIDPersistentIdentity',
    'IOpenIDRPSummary',
    'IOpenIDRPSummarySet',
    'ILoginServiceAuthorizeForm',
    'ILoginServiceLoginForm',
    ]

from zope.schema import Choice, Datetime, Int, TextLine
from zope.interface import Attribute, Interface
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from canonical.launchpad import _
from canonical.launchpad.fields import PasswordField
from canonical.launchpad.interfaces.account import IAccount
from canonical.launchpad.webapp.interfaces import ILaunchpadApplication
from lazr.restful.fields import Reference


class IOpenIDAuthorization(Interface):
    id = Int(title=u'ID', required=True)

    accountID = Int(title=u'Account', required=True, readonly=True)
    account = Attribute('The IAccount this is for')

    client_id = TextLine(title=u'Client ID', required=False)

    date_expires = Datetime(title=u'Expiry Date', required=True)
    date_created = Datetime(
            title=u'Date Created', required=True, readonly=True
            )

    trust_root = TextLine(title=u'OpenID Trust Root', required=True)


class IOpenIDAuthorizationSet(Interface):
    def isAuthorized(account, trust_root, client_id):
        """Check to see if the trust_root is authorized.

        Returns True or False.
        """

    def authorize(account, trust_root, expires, client_id=None):
        """Authorize the trust_root for the given account.

        If expires is None, the authorization never expires.

        If client_id is None, authorization is given to any client.
        If client_id is not None, authorization is only given to the client
        with the specified client_id (ie. the session cookie token).

        This method overrides any existing authorization for the given
        (account, trust_root, client_id).
        """

    def getByAccount(account):
        """Get the `IOpenIDAuthorization` objects for the given account.

        The authorization objects will be sorted in reverse of the
        order they were created.
        """


class IOpenIDRPSummary(Interface):
    """A summary of the interaction between an `Account` and an OpenID RP."""
    id = Int(title=u'ID', required=True)
    account = Reference(
        title=u'The IAccount used to login.', schema=IAccount,
        required=True, readonly=True)
    openid_identifier = TextLine(
        title=u'OpenID identifier', required=True, readonly=True)
    trust_root = TextLine(
        title=u'OpenID trust root', required=True, readonly=True)
    date_created = Datetime(
        title=u'Date Created', required=True, readonly=True)
    date_last_used = Datetime(title=u'Date last used', required=True)
    total_logins = Int(title=u'Total logins', required=True)

    def increment(date_used=None):
        """Increment the total_logins.

        :param date_used: an optional datetime the login happened. The current
            datetime is used if date_used is None.
        """


class IOpenIDRPSummarySet(Interface):
    """A set of OpenID RP Summaries."""

    def getByIdentifier(identifier, only_unknown_trust_roots=False):
        """Get all the IOpenIDRPSummary objects for an OpenID identifier.

        :param identifier: A string used as an OpenID identifier.
        :param only_unknown_trust_roots: if True, only records for trust roots
            which there is no IOpenIDRPConfig entry will be returned.
        :return: An iterator of IOpenIDRPSummary objects.
        """

    def record(account, trust_root):
        """Create or update an IOpenIDRPSummary.

        :param account: An `IAccount`.
        :param trust_root: A string used as an OpenID trust root.
        :return: An `IOpenIDRPSummary` or None.
        """

class IOpenIDApplication(ILaunchpadApplication):
    """Launchpad Login Service application root."""


class IOpenIDPersistentIdentity(Interface):
    """An object that represents a persistent user identity URL.

    This interface is generally needed by the UI.
    """
    account = Attribute('The `IAccount` for the user.')
    openid_identity_url = Attribute(
        'The OpenID identity URL for the user.')
    openid_identifier = Attribute(
        'The OpenID identifier used with the request.')


class ILoginServiceAuthorizeForm(Interface):
    """A schema used for the authorisation form showed to
    authenticated users."""

    nonce = TextLine(title=u'Nonce', required=False,
                     description=u'Unique value')


login_actions_vocabulary = SimpleVocabulary([
    SimpleTerm('login', 'login', 'Yes, my password is:'),
    SimpleTerm('createaccount', 'createaccount',
               'No, I want to create an account now'),
    SimpleTerm('resetpassword', 'resetpassword',
               "I've forgotten my password")])


class ILoginServiceLoginForm(ILoginServiceAuthorizeForm):
    """A schema used for the login/register form showed to
    unauthenticated users."""

    email = TextLine(title=u'What is your e-mail address?', required=True)
    password = PasswordField(title=u'Password', required=False)
    action = Choice(title=_('Action'), required=True,
                    vocabulary=login_actions_vocabulary)
