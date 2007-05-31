# list all team members: name, preferred email address
# Copyright (C) 2005, 2006, 2007 Canonical Software Ltd.

import sys

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.launchpad.interfaces import IPersonSet

################################################################################

class NoSuchTeamError(Exception): pass

def process_team(teamname, display_option=False):
    output = []
    people = getUtility(IPersonSet)
    memberset = people.getByName(teamname)
    if memberset == None:
        raise NoSuchTeamError

    if not display_option:
        for member in memberset.allmembers:
            if member.preferredemail is not None:
                email = member.preferredemail.email
            else:
                email = '--none--'
            output.append('%s, %s' % (member.name, email))
        return output
    elif display_option == 'email':
        for member in memberset.allmembers:
            if member.preferredemail:
                output.append(member.preferredemail.email)
            for email in member.validatedemails:
                output.append(email.email)
        return output
    elif display_option == 'full':
        for member in memberset.allmembers:
            prefmail = member.preferredemail
            if prefmail is not None:
                email = prefmail.email
            else:
                email = '--none--'
            if member.displayname:
                displayname = member.displayname.encode("ascii", "replace")
            else:
                displayname = ""
            ubuntite = "no"
            if member.signedcocs:
                for i in member.signedcocs:
                    if i.active:
                        ubuntite = "yes"
                        break
            else:
                ubuntite = "no"
            output.append('%s|%s|%s|%s|%s|%s' % (teamname, member.id, member.name, email,
                                         displayname, ubuntite))
        return output
