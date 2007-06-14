# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""List all team members: name, preferred email address."""

__metaclass__ = type
__all__ = ['process_team']

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.launchpad.interfaces import IPersonSet

output_templates = {
   'simple': '%(name)s, %(email)s',
   'email': '%(email)s',
   'full': '%(teamname)s|%(id)s|%(name)s|%(email)s|%(displayname)s|%(ubuntite)s'
   }


class NoSuchTeamError(Exception): 
    """Used if non-existent team name is specified."""
    pass

def process_team(teamname, display_option='simple'):
    output = []
    people = getUtility(IPersonSet)
    memberset = people.getByName(teamname)
    if memberset == None:
        raise NoSuchTeamError

    for member in memberset.allmembers:
        # Email
        if member.preferredemail is not None:
            email = member.preferredemail.email
        else:
            email = '--none--'
        # Ubuntite
        if member.signedcocs:
            for i in member.signedcocs:
                if i.active:
                    ubuntite = "yes"
                    break
        else:
            ubuntite = "no"
        params = dict(
            email=email, 
            name=member.name,
            teamname=teamname,
            id=member.id,
            displayname=member.displayname,
            ubuntite=ubuntite
            )
        output.append(output_templates[display_option] % params)
    # If we're only looking at email, remove --none-- entries
    # as we're only interested in emails
    if display_option == 'email':
        output = [x for x in output if x != '--none--']
    return sorted(output)

