# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Launchpad app specific testing infrastructure for Windmill."""

__metaclass__ = type
__all__ = [
    'AppWindmillLayer',
    ]


from canonical.testing.layers import BaseWindmillLayer


class AppWindmillLayer(BaseWindmillLayer):
    """Layer for App Windmill tests."""

    @classmethod
    def setUp(cls):
        cls.base_url = cls.appserver_root_url()
        super(AppWindmillLayer, cls).setUp()
