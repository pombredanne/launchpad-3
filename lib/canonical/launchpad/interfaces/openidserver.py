# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""OpenID related interfaces."""

__metaclass__ = type
__all__ = [
    'IOpenIDAuthorization',
    'IOpenIDAuthorizationSet',
    'IOpenIDPersistentIdentity',
    'IOpenIDRPConfig',
    'IOpenIDRPConfigSet',
    'IOpenIDRPSummary',
    'IOpenIDRPSummarySet',
    'ILaunchpadOpenIDStoreFactory',
    'ILoginServiceAuthorizeForm',
    'ILoginServiceLoginForm',
    ]

from zope.component import getUtility
from zope.schema import Bool, Choice, Datetime, Int, List, Text, TextLine
from zope.interface import Attribute, Interface
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from canonical.launchpad import _
from canonical.launchpad.fields import (
    BaseImageUpload, PasswordField, URIField, UniqueField)
from canonical.launchpad.interfaces.account import IAccount
from canonical.launchpad.interfaces.person import PersonCreationRationale
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


class ILaunchpadOpenIDStoreFactory(Interface):
    """Factory to create LaunchpadOpenIDStore instances."""

    def __call__():
        """Create a LaunchpadOpenIDStore instance."""


class TrustRootField(UniqueField, URIField):
    """An OpenID Relying Party trust root, which is unique."""

    attribute = 'trust_root'
    errormessage = _("%s is already in use for another Relying Party.")

    @property
    def _content_iface(self):
        return IOpenIDRPConfig

    def _getByAttribute(self, trust_root):
        return getUtility(IOpenIDRPConfigSet).getByTrustRoot(trust_root)


class RPLogoImageUpload(BaseImageUpload):

    dimensions = (400, 100)
    exact_dimensions = False
    max_size = 100*1024


sreg_fields_vocabulary = SimpleVocabulary([
    SimpleTerm('fullname', 'fullname', 'Full name'),
    SimpleTerm('nickname', 'nickname', 'Launchpad ID'),
    SimpleTerm('email', 'email', 'Email address'),
    SimpleTerm('timezone', 'timezone', 'Time zone'),
    SimpleTerm('x_address1', 'x_address1', 'Address line 1'),
    SimpleTerm('x_address2', 'x_address2', 'Address line 2'),
    SimpleTerm('x_city', 'x_city', 'City'),
    SimpleTerm('x_province', 'x_province', 'State/Province'),
    SimpleTerm('country', 'country', 'Country'),
    SimpleTerm('postcode', 'postcode', 'Postcode'),
    SimpleTerm('x_phone', 'x_phone', 'Phone number'),
    SimpleTerm('x_organization', 'x_organization', 'Organization')])


class IOpenIDRPConfig(Interface):
    """Configuration for a particular OpenID Relying Party."""
    id = Int(title=u'ID', required=True)
    trust_root = TrustRootField(
        title=_('Trust Root'), required=True,
        trailing_slash=True,
        description=_('The openid.trust_root value sent by the '
                      'Relying Party'))
    displayname = TextLine(
        title=_('Display Name'), required=True,
        description=_('A human readable name for the Relying Party'))
    description = Text(
        title=_('Description'), required=True,
        description=_('A description of the Relying Party, explaining why '
                      'the user should authenticate.'))
    logo = RPLogoImageUpload(
        title=_('Logo'), required=False,
        default_image_resource='/@@/nyet-logo',
        description=_('A banner that identifies the Relying Party, '
                      'no larger than 400x100 pixels.'))
    allowed_sreg = List(
        title=_('Allowed Sreg Fields'),
        description=_('The simple registration fields that may be '
                      'transferred to this Relying Party'),
        value_type=Choice(vocabulary=sreg_fields_vocabulary))
    creation_rationale = Choice(
        title=_('Creation Rationale'),
        description=_('The creation rationale to use for user accounts '
                      'created while logging in to this Relying Party'),
        vocabulary=PersonCreationRationale)
    can_query_any_team = Bool(
        title=_('Query Any Team'),
        description=_(
            'Teammembership of any team can be requested, including '
            'private teams.'),
        required=True, readonly=False)


class IOpenIDRPConfigSet(Interface):
    """The set of OpenID Relying Party configurations."""
    def new(trust_root, displayname, description, logo=None,
            allowed_sreg=None, creation_rationale=PersonCreationRationale
            .OWNER_CREATED_UNKNOWN_TRUSTROOT):
        """Create a new IOpenIDRPConfig"""

    def get(id):
        """Get the IOpenIDRPConfig with a particular ID."""

    def getAll():
        """Return a sequence of all IOpenIDRPConfigs."""

    def getByTrustRoot(trust_root):
        """Return the IOpenIDRPConfig for a particular trust root"""


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


class IOpenIDPersistentIdentity(Interface):
    """An object that represents a persistent user identity URL.

    This interface is generally needed by the UI.
    """
    account = Attribute('The `IAccount` for the user.')
    # XXX sinzui 2008-09-04 bug=264783:
    # Remove old_openid_identity_url and new_*.
    old_openid_identifier = Attribute(
        'The old openid_identifier for the `IAccount`.')
    old_openid_identity_url = Attribute(
        'The old OpenID identity URL for the user.')
    new_openid_identifier = Attribute(
        'The new openid_identifier for the `IAccount`.')
    new_openid_identity_url = Attribute(
        'The new OpenID identity URL for the user.')
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
