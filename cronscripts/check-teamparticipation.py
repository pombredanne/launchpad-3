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

import bz2

import _pythonpath
import cPickle as pickle

from lp.registry.scripts.teamparticipation import (
    check_teamparticipation_circular,
    check_teamparticipation_consistency,
    check_teamparticipation_self,
    fetch_team_participation_info,
    )
from lp.services.scripts.base import LaunchpadScript


def save(obj, filename):
    """Save a bz2 compressed pickle of `obj` to `filename`."""
    fout = bz2.BZ2File(filename, "w")
    try:
        pickle.dump(obj, fout, pickle.HIGHEST_PROTOCOL)
    finally:
        fout.close()


def load(filename):
    """Load and return a bz2 compressed pickle from `filename`."""
    fin = bz2.BZ2File(filename, "r")
    try:
        return pickle.load(fin)
    finally:
        fin.close()


class CheckTeamParticipationScript(LaunchpadScript):
    description = "Check for invalid/missing TeamParticipation entries."

    def add_my_options(self):
        self.parser.add_option(
            "--load-participation-info",
            dest="load_participation_info", metavar="FILE",
            help=(
                "File from which to load participation information "
                "instead of going to the database."))
        self.parser.add_option(
            "--save-participation-info",
            dest="save_participation_info", metavar="FILE",
            help=(
                "File in which to save participation information, for "
                "later processing with --load-participation-info."))

    def main(self):
        """Perform various checks on the `TeamParticipation` table."""
        if self.options.load_participation_info:
            participation_info = load(self.options.load_participation_info)
        else:
            participation_info = fetch_team_participation_info(self.logger)

        check_teamparticipation_self(self.logger)
        check_teamparticipation_circular(self.logger)
        check_teamparticipation_consistency(self.logger, participation_info)

        if self.options.save_participation_info:
            save(participation_info, self.options.save_participation_info)


if __name__ == '__main__':
    CheckTeamParticipationScript("check-teamparticipation").run()
