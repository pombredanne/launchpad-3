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

    @property
    def tip_commit_info(self):
        return {
            "sha1": self.context.commit_sha1,
            "author": self.context.author,
            "author_date": self.context.author_date,
            "commit_message": self.context.commit_message,
            }
