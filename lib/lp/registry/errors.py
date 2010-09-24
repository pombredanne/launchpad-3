# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'TeamMembershipTransitionError',
    ]
    
from lazr.restful.declarations import webservice_error


class TeamMembershipTransitionError(ValueError):
    """comment"""
    webservice_error(403) # 403 Forbidden
