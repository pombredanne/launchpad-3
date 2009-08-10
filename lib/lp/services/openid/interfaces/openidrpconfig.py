# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""OpenIDRPConfig related interfaces."""

__metaclass__ = type
__all__ = [
    'IOpenIDRPConfig',
    'IOpenIDRPConfigSet',
    ]

from zope.component import getUtility
from zope.schema import Bool, Choice, Int, List, Text, TextLine
from zope.interface import Interface
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from canonical.launchpad import _
from canonical.launchpad.fields import (
    BaseImageUpload, URIField, UniqueField)
from lp.registry.interfaces.person import PersonCreationRationale


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
    auto_authorize = Bool(
        title=_('Automatically authorize requests'),
        description=_(
            'Authentication requests for this RP are responded to '
            'automatically without explicit user authorization'),
        required=True, readonly=False)


class IOpenIDRPConfigSet(Interface):
    """The set of OpenID Relying Party configurations."""
    def new(trust_root, displayname, description, logo=None,
            allowed_sreg=None, creation_rationale=PersonCreationRationale
            .OWNER_CREATED_UNKNOWN_TRUSTROOT, can_query_any_team=False,
            auto_authorize=False):
        """Create a new IOpenIDRPConfig"""

    def get(id):
        """Get the IOpenIDRPConfig with a particular ID."""

    def getAll():
        """Return a sequence of all IOpenIDRPConfigs."""

    def getByTrustRoot(trust_root):
        """Return the IOpenIDRPConfig for a particular trust root"""


