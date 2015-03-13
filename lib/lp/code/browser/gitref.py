# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git reference views."""

__metaclass__ = type

__all__ = [
    'GitRefView',
    ]

from lp.services.webapp import LaunchpadView


class GitRefView(LaunchpadView):

    @property
    def label(self):
        return self.context.display_name
