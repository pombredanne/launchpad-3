# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = []

from zope.component import getUtility

from canonical.launchpad import _
from canonical.launchpad.interfaces import IOpenIDRPConfig, IOpenIDRPConfigSet
from canonical.launchpad.webapp import (
    LaunchpadEditFormView, LaunchpadFormView, Navigation, action,
    canonical_url, custom_widget)
from canonical.widgets import LabeledMultiCheckBoxWidget


class OpenIDRPConfigSetNavigation(Navigation):
    usedfor = IOpenIDRPConfigSet

    def traverse(self, config_id):
        """Traverse to RP configs by ID."""
        try:
            config_id = int(config_id)
        except ValueError:
            return None

        return getUtility(IOpenIDRPConfigSet).get(config_id)


class OpenIDRPConfigAddView(LaunchpadFormView):

    schema = IOpenIDRPConfig
    field_names = ['trust_root', 'displayname', 'description', 'logo',
                   'allowed_sreg', 'creation_rationale']
    custom_widget('allowed_sreg', LabeledMultiCheckBoxWidget)

    @action(_('Create'), name='create')
    def create_action(self, action, data):
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

    schema = IOpenIDRPConfig
    field_names = ['trust_root', 'displayname', 'description', 'logo',
                   'allowed_sreg', 'creation_rationale']
    custom_widget('allowed_sreg', LabeledMultiCheckBoxWidget)

    @action(_('Save'), name='save')
    def save_action(self, action, data):
        if self.updateContextFromData(data):
            self.request.response.addInfoNotification(
                _('Updated RP configuration for %(trust_root)s.'),
                trust_root=self.context.trust_root)

    @action(_('Remove'), name='remove')
    def remove_action(self, action, data):
        trust_root = self.context.trust_root
        self.context.destroySelf()
        self.request.response.addInfoNotification(
            _('Removed RP configuration for %(trust_root)s.'),
            trust_root=trust_root)

    @property
    def next_url(self):
        return canonical_url(getUtility(IOpenIDRPConfigSet))
