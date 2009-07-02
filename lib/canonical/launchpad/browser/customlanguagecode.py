# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'CustomLanguageCodeAddView',
    'CustomLanguageCodeIndexView',
	]


from canonical.launchpad.interfaces.customlanguagecode import (
    ICustomLanguageCode)

from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadFormView, LaunchpadView)
from canonical.launchpad.webapp.menu import structured


class CustomLanguageCodeIndexView(LaunchpadView):
    pass


class CustomLanguageCodeAddView(LaunchpadFormView):

    schema = ICustomLanguageCode
    field_names = ['language_code', 'language']
    label = "Add a custom language code"

    create = True

    def validate(self, data):
        self.language_code = data.get('language_code')
        self.language = data.get('language')
        if self.language_code is not None:
            self.language_code = self.language_code.strip()

        existing_code = self.context.getCustomLanguageCode(self.language_code)
        if existing_code is not None:
            self.create = False
            if existing_code.language != self.language:
                self.setFieldError(
                    'language_code',
                    structured(
                        "There already is a custom language code '%s'." % 
                            self.language_code))

    @action('Add', name='add')
    def add_action(self, action, data):
        if self.create:
            self.context.createCustomLanguageCode(
                self.language_code, self.language)

    @action('Cancel', name='cancel', validator='validate_cancel')
    def cancel_action(self, action, data):
        pass

    @property
    def action_url(self):
        return "%s/+addcustomlanguagecode" % canonical_url(self.context)

    @property
    def next_url(self):
        """See `LaunchpadFormView`."""
        return "%s/+customlanguagecodes" % canonical_url(self.context)
