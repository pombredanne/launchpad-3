# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Code-specific testing infrastructure for Windmill."""

__metaclass__ = type
__all__ = [
    'CodeWindmillLayer',
    ]


from canonical.testing.layers import BaseWindmillLayer


class CodeWindmillLayer(BaseWindmillLayer):
    """Layer for Code Windmill tests."""

    @classmethod
    def setUp(cls):
        cls.base_url = cls.appserver_root_url('code')
        super(CodeWindmillLayer, cls).setUp()

