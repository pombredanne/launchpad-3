# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""OpenId related interfaces."""

__metaclass__ = type
__all__ = [
        'IOpenIdAuthorization',
        'IOpenIdAuthorizationSet',
        'IOpenIDRPConfig',
        'IOpenIDRPConfigSet',
        'ILaunchpadOpenIdStoreFactory',
        'ILoginServiceAuthorizeForm',
        'ILoginServiceLoginForm',
        ]

from zope.schema import Choice, Datetime, Int, List, Object, TextLine
from zope.interface import Attribute, Interface
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from canonical.launchpad import _
from canonical.launchpad.fields import PasswordField, BaseImageUpload
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad.interfaces.person import PersonCreationRationale


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


class RPLogoImageUpload(BaseImageUpload):

    dimensions = (400, 100)
    exact_dimensions = False
    max_size = 100*1024
    default_image_resource = '/@@/nyet-logo'


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
    trust_root = TextLine(
        title=_('Trust Root'), required=True,
        description=_('The openid.trust_root value sent by the Relying Party'))
    displayname = TextLine(
        title=_('Display Name'), required=True,
        description=_('A human readable name for the Relying Party'))
    description = TextLine(
        title=_('Description'), required=True,
        description=_('A description of the Relying Party, explaining why '
                      'the user should authenticate.'))
    logo = RPLogoImageUpload(
        title=_('logo'), required=False,
        description=_('A banner that identifies the Relying Party'))
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


class IOpenIDRPConfigSet(Interface):
    """The set of OpenID Relying Party configurations."""
    def new(trust_root, displayname, description, logo=None, allowed_sreg=None,
            creation_rationale=PersonCreationRationale.OWNER_CREATED_UNKNOWN_TRUSTROOT):
        """Create a new IOpenIdRPConfig"""

    def get(id):
        """Get the IOpenIdRPConfig with a particular ID."""

    def getAll():
        """Return a sequence of all IOpenIdRPConfigs."""

    def getByTrustRoot(trust_root):
        """Return the IOpenIdRPConfig for a particular trust root"""


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
