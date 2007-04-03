# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for items that can be displayed as images."""

__metaclass__ = type

__all__ = [
    'BrandingChangeView',
    ]

from canonical.launchpad.interfaces import IHasIcon, IHasLogo, IHasMugshot

from canonical.widgets.image import ImageChangeWidget
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, LaunchpadEditFormView)


class BrandingChangeView(LaunchpadEditFormView):
    """This is a base class that MUST be subclassed for each object, because
    each object will have a different description for its branding that is
    part of its own interface.

    For each subclass, specify the schema ("IPerson") and the field_names
    (some subset of icon, logo, mugshot).
    """

    label = 'Change branding in Launchpad'

    custom_widget('icon', ImageChangeWidget, ImageChangeWidget.EDIT_STYLE)
    custom_widget('logo', ImageChangeWidget, ImageChangeWidget.EDIT_STYLE)
    custom_widget('mugshot', ImageChangeWidget, ImageChangeWidget.EDIT_STYLE)

    @action("Change Branding", name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)

    @property
    def next_url(self):
        return canonical_url(self.context)

