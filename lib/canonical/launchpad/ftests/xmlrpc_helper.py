# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper functions for testing XML-RPC services."""

import xmlrpclib

from canonical.launchpad.interfaces import (
    IPersonSet, IMailingListSet, MailingListStatus, TeamSubscriptionPolicy)
from zope.component import getUtility


def fault_catcher(func):
    """Decorator for displaying Faults in a cross-compatible way.

    When running the same doctest with the ServerProxy, faults are turned into
    exceptions by the XMLRPC machinery, but with the direct view the faults
    are just returned.  This causes an impedence mismatch with exception
    display in the doctest that cannot be papered over by using ellipses.  So
    to make this work in a consistent way, a subclass of the view class is
    used which prints faults to match the output of ServerProxy (proper
    exceptions aren't really necessary).
    """
    def caller(self, *args, **kws):
        result = func(self, *args, **kws)
        if isinstance(result, xmlrpclib.Fault):
            # Fake this to look like exception output.  The second line is
            # necessary to match ellipses in the doctest, but its contents are
            # completely ignored; /something/ just has to be there.
            print 'Traceback (most recent call last):'
            print 'ignore'
            print 'Fault:', result
        else:
            return result
    return caller


def mailingListPrintActions(pending_actions):
    """A helper function for the mailinglist-xmlrpc.txt doctest.

    This helps print the data structure returned from .getPendingActions() in
    a more succinct way so as to produce a more readable doctest.  It also
    eliminates trivial representational differences caused by the doctest
    being run both with an internal view and via an XMLRPC proxy.

    The problem is that the types of the values in the pending_actions
    dictionary will be different depending on which way the doctest is run.
    The contents will be the same but when run via an XMLRPC proxy, the values
    will be strs, and when run via the internal view, they will be unicodes.
    If you don't coerce the values, they'll print differently, superficially
    breaking the doctest.  For example, unicodes will print with a u-prefix
    (e.g. u'Welcome to Team One') while the strs will print without a prefix
    (e.g. 'Welcome to Team One').

    The only way to write a doctest so that both correct results will pass is
    to coerce one string type to the other, and coercing to unicodes seems
    like the most straightforward thing to do.  The keys of the dictionary do
    not need to be coerced because they will be strs in both cases.
    """
    for action in sorted(pending_actions):
        for team in sorted(pending_actions[action]):
            if action in ('create', 'modify'):
                team, modification = team
                modification = dict((k, unicode(v))
                                    for k, v in modification.items())
                print team, '-->', action, modification
            else:
                print team, '-->', action


def mailingListNewTeam(team_name, with_list=False):
    """A helper function for the mailinglist related doctests.

    This just provides a convenience function for creating the kinds of teams
    we need to use in the doctest.
    """
    displayname = ' '.join(word.capitalize() for word in team_name.split('-'))
    # XXX BarryWarsaw Set the team's subscription policy to OPEN because of
    # bug 125505.
    policy = TeamSubscriptionPolicy.OPEN
    personset = getUtility(IPersonSet)
    ddaa = personset.getByName('ddaa')
    team = personset.newTeam(ddaa, team_name, displayname,
                             subscriptionpolicy=policy)
    if not with_list:
        return team
    # Create the associated mailing list.
    carlos = personset.getByName('carlos')
    team_list = getUtility(IMailingListSet).new(team)
    team_list.review(carlos, MailingListStatus.APPROVED)
    team_list.startConstructing()
    team_list.transitionToStatus(MailingListStatus.ACTIVE)
    return team, team_list


