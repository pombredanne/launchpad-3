# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'InformationTypePortlet',
    ]

from lazr.restful.interfaces import IJSONRequestCache

from lp.bugs.interfaces.bug import IBug
from lp.code.interfaces.branch import IBranch
from lp.registry.enums import (
    InformationType,
    PRIVATE_INFORMATION_TYPES,
    )
from lp.registry.vocabularies import InformationTypeVocabulary
from lp.services.features import getFeatureFlag


class InformationTypePortlet:

    def initialize(self):
        cache = IJSONRequestCache(self.request)
        cache.objects['information_types'] = [
            {'value': term.value, 'description': term.description,
            'name': term.title,
            'description_css_class': 'choice-description'}
            for term in InformationTypeVocabulary()]
        cache.objects['private_types'] = [
            type.title for type in PRIVATE_INFORMATION_TYPES]
        cache.objects['show_information_type_in_ui'] = (
            self.show_information_type_in_ui)

    @property
    def show_information_type_in_ui(self):
        feature_flag_base = 'disclosure.show_information_type_in_ui.enabled'
        if IBug.providedBy(self.context):
            pass
        elif IBranch.providedBy(self.context):
            feature_flag_base = feature_flag_base.replace('ui', 'branch_ui')
        else:
            raise NotImplemented()
        return bool(getFeatureFlag(feature_flag_base))

    @property
    def show_userdata_as_private(self):
        return bool(getFeatureFlag(
            'disclosure.display_userdata_as_private.enabled'))

    @property
    def information_type(self):
        # This can be replaced with just a return when the feature flag is
        # dropped.
        title = self.context.information_type.title
        if (
            self.context.information_type == InformationType.USERDATA and
            self.show_userdata_as_private):
            return 'Private'
        return title

    @property
    def information_type_description(self):
        # This can be replaced with just a return when the feature flag is
        # dropped.
        description = self.context.information_type.description
        if (
            self.context.information_type == InformationType.USERDATA and
            self.show_userdata_as_private):
                description = (
                    description.replace('user data', 'private information'))
        return description
