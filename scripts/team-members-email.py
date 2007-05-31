#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

import logging
import sys

import _pythonpath

from canonical.config import config

from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.launchpad.scripts.teammembersemail import process_team, NoSuchTeamError


class TeamMembersEmailScript(LaunchpadScript):

    description = "Create a list of members of a team."
    usage = "usage: %s team-name [team-name-2] .. [team-name-n]" % sys.argv[0]
    loglevel = logging.INFO

    def main(self):

        teamnames = sys.argv[1:]
        if len(teamnames) < 1: self.parser.error('No team specified')

        emails = []
        for teamname in teamnames:
            try:
                emails.extend(process_team(teamname))
            except NoSuchTeamError:
                print "Error, no such team: %s" % teamname
                sys.exit(1)
        print "\n".join(sorted(list(set(emails))))
        return 0

if __name__ == '__main__':
    script = TeamMembersEmailScript('canonical.launchpad.scripts.teammembersemail')
    script.run()
