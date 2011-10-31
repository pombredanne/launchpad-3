#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0103,W0403

"""Check for invalid/missing TeamParticipation entries.

Invalid TP entries are the ones for which there are no active TeamMemberships
leading to.

This script is usually run on staging to find discrepancies between the
TeamMembership and TeamParticipation tables which are a good indication of
bugs in the code which maintains the TeamParticipation table.

Ideally there should be database constraints to prevent this sort of
situation, but that's not a simple thing and this should do for now.
"""

import _pythonpath

from lp.registry.scripts.teamparticipation import check_teamparticipation
from lp.services.scripts.base import LaunchpadScript


class CheckTeamParticipationScript(LaunchpadScript):
    description = "Check for invalid/missing TeamParticipation entries."

    def main(self):
        check_teamparticipation(self.logger)


if __name__ == '__main__':
    CheckTeamParticipationScript("check-teamparticipation").run()
