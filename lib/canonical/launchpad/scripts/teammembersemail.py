# list all team members: name, preferred email address
# Copyright (C) 2005, 2006, 2007 Canonical Software Ltd.

import sys

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.launchpad.interfaces import IPersonSet

################################################################################

class NoSuchTeamError(Exception): pass

def process_team(teamname):
    emails = []
    people = getUtility(IPersonSet)
    memberset = people.getByName(teamname)
    if memberset == None:
        raise NoSuchTeamError
    for member in memberset.allmembers:
        if member.preferredemail:
                emails.append(member.preferredemail.email)
        for email in member.validatedemails:
                emails.append(email.email)
    return emails
