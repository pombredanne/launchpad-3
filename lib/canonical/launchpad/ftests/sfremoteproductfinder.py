# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Testing helpers for sfremoteproductfinder."""

__metaclass__ = type
__all__ = ['TestSFRemoteProductFinder']

import os
import re
from canonical.launchpad.scripts.sfremoteproductfinder import (
    SourceForgeRemoteProductFinder)

class TestSFRemoteProductFinder(SourceForgeRemoteProductFinder):

    def _getPage(self, page):
        self.logger.info("Getting page %s" % page)

        project_re = re.compile('projects/([a-z]+)')
        tracker_re = re.compile('/?tracker/\?group_id=([0-9]+)')

        project_match = project_re.match(page)
        tracker_match = tracker_re.match(page)

        if project_match is not None:
            project = project_match.groups()[0]
            file_path = os.path.join(
                os.path.dirname(__file__), 'testfiles',
                'sourceforge-project-%s.html' % project)
        elif tracker_match is not None:
            group_id = tracker_match.groups()[0]
            file_path = os.path.join(
                os.path.dirname(__file__), 'testfiles',
                'sourceforge-tracker-%s.html' % group_id)

        return open(file_path, 'r').read()

