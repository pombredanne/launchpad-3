# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Translations-specific testing infrastructure for Windmill."""

__metaclass__ = type
__all__ = [
    'TranslationsWindmillLayer',
    ]


from canonical.testing.layers import BaseWindmillLayer


class TranslationsWindmillLayer(BaseWindmillLayer):
    """Layer for Translations Windmill tests."""

    @classmethod
    def setUp(cls):
        cls.base_url = cls.appserver_root_url('translations')
        super(TranslationsWindmillLayer, cls).setUp()

