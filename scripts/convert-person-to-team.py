#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Script to convert a person into a team.

Only people whose account_status is NOACCOUNT can be turned into teams.
"""


import _pythonpath

from zope.component import getUtility

from canonical.launchpad.scripts.base import (
    LaunchpadScript, LaunchpadScriptFailure)
from canonical.launchpad.interfaces import AccountStatus, IPersonSet


class ConvertPersonToTeamScript(LaunchpadScript):

    usage = '%prog <person-to-convert> <team-owner>'

    def main(self):
        if len(self.args) != 2:
            raise LaunchpadScriptFailure(
                "You must specify the name of the person to be converted "
                "and the person/team who should be its teamowne.")

        person_set = getUtility(IPersonSet)
        person_name, owner_name = self.args
        person = person_set.getByName(person_name)
        owner = person_set.getByName(owner_name)

        if person.account_status != AccountStatus.NOACCOUNT:
            raise LaunchpadScriptFailure(
                "Only people which have no account can be turned into teams.")

        person.convertToTeam(owner)
        self.txn.commit()


if __name__ == '__main__':
    script = ConvertPersonToTeamScript('convert-person-to-team')
    script.lock_and_run()

