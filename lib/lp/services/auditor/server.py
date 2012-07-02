# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Auditor server fixture."""

__metaclass__ = type
__all__ = [
    'AuditorServer',
    ]

import os
from textwrap import dedent

from auditorfixture.server import AuditorFixture

import lp


class AuditorServer(AuditorFixture):
    """An Auditor server fixture with Launchpad-specific config.

    :ivar service_config: A snippet of .ini that describes the `auditor`
        configuration.
    """

    def __init__(self, port=None, logfile=None, manage_bin=None):
        manage_bin = os.path.join(
            os.path.dirname(lp.__file__), '../../bin/auditor-manage')
        super(AuditorServer, self).__init__(port, logfile, manage_bin)

    def setUp(self):
        super(AuditorServer, self).setUp()
        setattr(
            self, 'service_config',
            dedent("""\
                [auditor]
                port: %d
                """ % (self.config.port)))
