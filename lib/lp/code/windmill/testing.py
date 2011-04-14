# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Code-specific testing infrastructure for Windmill."""

__metaclass__ = type
__all__ = [
    'CodeWindmillLayer',
    'CodeYUILayer',
    ]


from canonical.testing.layers import (
    BaseWindmillLayer,
    BaseYUITestLayer,
    )


class CodeWindmillLayer(BaseWindmillLayer):
    """Layer for Code Windmill tests."""

    @classmethod
    def setUp(cls):
        cls.facet = 'code'
        cls.base_url = cls.appserver_root_url(cls.facet)
        super(CodeWindmillLayer, cls).setUp()


class CodeYUILayer(BaseYUITestLayer):
    """Layer for Code YUI tests."""

    @classmethod
    def setUp(cls):
        cls.facet = 'code'
        cls.base_url = cls.appserver_root_url(cls.facet)
        super(CodeYUILayer, cls).setUp()
