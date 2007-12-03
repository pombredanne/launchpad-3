# Copyright 2007 Canonical Ltd.  All rights reserved.

"""View classes used to edit `IOpenIDRPConfig` objects."""

__metaclass__ = type
__all__ = []

from zope.component import getUtility

from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    IOpenIDRPConfig, IOpenIDRPConfigSet, PersonCreationRationale)
from canonical.launchpad.webapp import (
    LaunchpadEditFormView, LaunchpadFormView, Navigation, action,
    canonical_url, custom_widget)
from canonical.widgets import LabeledMultiCheckBoxWidget
from canonical.widgets.image import ImageChangeWidget


class OpenIDRPConfigSetNavigation(Navigation):
    """Navigation for `IOpenIDRPConfigSet`."""
    usedfor = IOpenIDRPConfigSet

    def traverse(self, config_id):
        """Traverse to RP configs by ID."""
        try:
            config_id = int(config_id)
        except ValueError:
            return None

        return getUtility(IOpenIDRPConfigSet).get(config_id)


class OpenIDRPConfigAddView(LaunchpadFormView):
    """View class for adding new RP configurations."""

    schema = IOpenIDRPConfig
    field_names = ['trust_root', 'displayname', 'description', 'logo',
                   'allowed_sreg', 'creation_rationale']
    custom_widget('logo', ImageChangeWidget, ImageChangeWidget.ADD_STYLE)
    custom_widget('allowed_sreg', LabeledMultiCheckBoxWidget)

    initial_values = {
        'creation_rationale':
            PersonCreationRationale.OWNER_CREATED_UNKNOWN_TRUSTROOT
        }

    @action(_('Create'), name='create')
    def create_action(self, action, data):
        """Create the new RP configuration."""
        rpconfig = getUtility(IOpenIDRPConfigSet).new(
            trust_root=data['trust_root'],
            displayname=data['displayname'],
            description=data['description'],
            logo=data['logo'],
            allowed_sreg=data['allowed_sreg'],
            creation_rationale=data['creation_rationale'])
        self.request.response.addInfoNotification(
            _('Created RP configuration for %(trust_root)s.'),
            trust_root=data['trust_root'])

    @property
    def next_url(self):
        return canonical_url(getUtility(IOpenIDRPConfigSet))


class OpenIDRPConfigEditView(LaunchpadEditFormView):
    """View class for editing or removing RP configurations."""

    schema = IOpenIDRPConfig
    field_names = ['trust_root', 'displayname', 'description', 'logo',
                   'allowed_sreg', 'creation_rationale']
    custom_widget('logo', ImageChangeWidget, ImageChangeWidget.EDIT_STYLE)
    custom_widget('allowed_sreg', LabeledMultiCheckBoxWidget)

    @action(_('Save'), name='save')
    def save_action(self, action, data):
        """Save the RP configuration."""
        if self.updateContextFromData(data):
            self.request.response.addInfoNotification(
                _('Updated RP configuration for %(trust_root)s.'),
                trust_root=self.context.trust_root)

    @action(_('Remove'), name='remove')
    def remove_action(self, action, data):
        """Remove the RP configuration."""
        trust_root = self.context.trust_root
        self.context.destroySelf()
        self.request.response.addInfoNotification(
            _('Removed RP configuration for %(trust_root)s.'),
            trust_root=trust_root)

    @property
    def next_url(self):
        return canonical_url(getUtility(IOpenIDRPConfigSet))
