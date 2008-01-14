# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""List all team members: name, preferred email address."""

__metaclass__ = type
__all__ = ['process_team']

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.launchpad.interfaces import IPersonSet


OUTPUT_TEMPLATES = {
   'simple': '%(name)s, %(email)s',
   'email': '%(email)s',
   'full': '%(teamname)s|%(id)s|%(name)s|%(email)s|%(displayname)s|%(ubuntite)s'
   }


class NoSuchTeamError(Exception):
    """Used if non-existent team name is specified."""


def process_team(teamname, display_option='simple'):
    output = []
    people = getUtility(IPersonSet)
    memberset = people.getByName(teamname)
    if memberset == None:
        raise NoSuchTeamError

    template = OUTPUT_TEMPLATES[display_option]
    for member in memberset.allmembers:
        # Email
        if member.preferredemail is not None:
            email = member.preferredemail.email
        else:
            email = '--none--'
        if display_option == 'email':
            for validatedemail in member.validatedemails:
                params = dict(
                    email=validatedemail.email,
                    )
                output.append(template % params)
        # Ubuntite
        ubuntite = "no"
        if member.signedcocs:
            for i in member.signedcocs:
                if i.active:
                    ubuntite = "yes"
                    break
        params = dict(
            email=email,
            name=member.name,
            teamname=teamname,
            id=member.id,
            displayname=member.displayname.encode("ascii", "replace"),
            ubuntite=ubuntite
            )
        output.append(template % params)
    # If we're only looking at email, remove --none-- entries
    # as we're only interested in emails
    if display_option == 'email':
        output = [line for line in output if line != '--none--']
    return sorted(output)

