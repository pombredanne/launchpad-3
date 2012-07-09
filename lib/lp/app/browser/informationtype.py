# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'InformationTypePortletMixin',
    ]

from lazr.restful.interfaces import IJSONRequestCache

from lp.registry.enums import (
    InformationType,
    PRIVATE_INFORMATION_TYPES,
    )
from lp.registry.vocabularies import InformationTypeVocabulary
from lp.services.features import getFeatureFlag


class InformationTypePortletMixin:

    def initialize(self):
        cache = IJSONRequestCache(self.request)
        cache.objects['information_types'] = [
            {'value': term.value, 'description': term.description,
            'name': term.title,
            'description_css_class': 'choice-description'}
            for term in InformationTypeVocabulary(self.context)]
        cache.objects['private_types'] = [
            type.title for type in PRIVATE_INFORMATION_TYPES]
        cache.objects['show_userdata_as_private'] = (
            self.show_userdata_as_private)

    @property
    def show_userdata_as_private(self):
        return bool(getFeatureFlag(
            'disclosure.display_userdata_as_private.enabled'))

    @property
    def information_type(self):
        # This can be replaced with just a return when the feature flag is
        # dropped.
        title = self.context.information_type.title
        if (self.context.information_type == InformationType.USERDATA and
            self.show_userdata_as_private):
            return 'Private'
        return title

    @property
    def information_type_description(self):
        # This can be replaced with just a return when the feature flag is
        # dropped.
        description = self.context.information_type.description
        if (self.context.information_type == InformationType.USERDATA and
            self.show_userdata_as_private):
                description = (
                    'Visible only to users with whom the project has '
                    'shared private information.')
        return description

    @property
    def information_type_css(self):
        if self.context.information_type in PRIVATE_INFORMATION_TYPES:
            return 'sprite private'
        else:
            return 'sprite public'
