# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper functions for testing XML-RPC services."""

__metaclass__ = type
__all__ = [
    'apply_for_list',
    'fault_catcher',
    'get_alternative_email',
    'mailman',
    'new_list_for_team',
    'new_team',
    'print_actions',
    'print_dispositions',
    'print_info',
    'review_list',
    ]


import xmlrpclib

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import flush_database_updates
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.interfaces.mailinglist import (
    IMailingListSet,
    IMessageApprovalSet,
    MailingListStatus,
    PostedMessageStatus,
    )
from lp.registry.interfaces.person import (
    IPersonSet,
    TeamSubscriptionPolicy,
    )
from lp.registry.xmlrpc.mailinglist import MailingListAPIView


COMMASPACE = ', '


def fault_catcher(func):
    """Decorator for displaying Faults in a cross-compatible way.

    When running the same doctest with the ServerProxy, faults are turned into
    exceptions by the XMLRPC machinery, but with the direct view the faults
    are just returned.  This causes an impedance mismatch with exception
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


def print_actions(pending_actions):
    """A helper function for the mailing list tests.

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
        for value in sorted(pending_actions[action]):
            if action in ('create', 'modify'):
                team, modification = value
                modification = dict((k, unicode(v))
                                    for k, v in modification.items())
                print team, '-->', action, modification
            elif action == 'unsynchronized':
                team, state = value
                print team, '-->', action, state
            else:
                print value, '-->', action


def print_info(info, full=False):
    """A helper function for the mailing list tests.

    This prints the results of the XMLRPC .getPendingActions() call.

    Note that in order to make the tests that use this method a little
    clearer, we specifically suppress printing of the mail-archive recipient
    when `full` is False (the default).
    """
    status_mapping = {
        0: 'RECIPIENT',
        2: 'X',
        }
    for team_name in sorted(info):
        print team_name
        subscribees = info[team_name]
        for address, realname, flags, status_id in subscribees:
            status = status_mapping.get(status_id, '??')
            if realname == '':
                realname = '(n/a)'
            if (not full and
                config.mailman.archive_address and
                address == config.mailman.archive_address):
                # Don't print this information
                pass
            else:
                print '    %-25s %-15s' % (address, realname), flags, status


def print_dispositions(dispositions):
    """Pretty print `IMailingListAPIView.getMessageDispositions()`."""
    for message_id in sorted(dispositions):
        list_name, action = dispositions[message_id]
        print message_id, list_name, action


def print_addresses(data):
    """Print the addresses in a dictionary.

    This is used for the results returned by `IMailingListSet` methods
    `getSenderAddresses()` and `getSubscribedAddresses()`.

    :param data: The data as returned by the above methods.
    :type data: dictionary of 2-tuples
    """
    for team_name in sorted(data):
        print team_name
        print COMMASPACE.join(sorted(
            address for (real_name, address) in data[team_name]))


def new_team(team_name, with_list=False):
    """A helper function for the mailinglist doctests.

    This just provides a convenience function for creating the kinds of teams
    we need to use in the doctest.
    """
    displayname = ' '.join(word.capitalize() for word in team_name.split('-'))
    # XXX BarryWarsaw 2007-09-27 bug 125505: Set the team's subscription
    # policy to OPEN.
    policy = TeamSubscriptionPolicy.OPEN
    personset = getUtility(IPersonSet)
    team_creator = personset.getByName('no-priv')
    team = personset.newTeam(team_creator, team_name, displayname,
                             subscriptionpolicy=policy)
    if not with_list:
        return team
    else:
        return team, new_list_for_team(team)


def new_list_for_team(team):
    """A helper that creates a new, active mailing list for a team.

    Used in doctests.
    """
    # Any member of the mailing-list-experts team can review a list
    # registration.  It doesn't matter which one.
    experts = getUtility(ILaunchpadCelebrities).registry_experts
    reviewer = list(experts.allmembers)[0]
    list_set = getUtility(IMailingListSet)
    team_list = list_set.new(team)
    team_list.startConstructing()
    team_list.transitionToStatus(MailingListStatus.ACTIVE)
    flush_database_updates()
    return team_list


def apply_for_list(browser, team_name, rooturl='http://launchpad.dev/',
                   private=False):
    """Create a team and apply for its mailing list.

    This should only be used in page tests.
    """
    displayname = ' '.join(word.capitalize() for word in team_name.split('-'))
    browser.open(rooturl + 'people/+newteam')
    browser.getControl(name='field.name').value = team_name
    browser.getControl('Display Name').value = displayname
    if private:
        browser.getControl('Visibility').value = ['PRIVATE']
        browser.getControl(name='field.subscriptionpolicy').value = [
            'RESTRICTED']
    else:
        browser.getControl(
            name='field.subscriptionpolicy').displayValue = ['Open Team']
    browser.getControl('Create').click()
    # Create the team's mailing list.
    browser.open('%s~%s/+mailinglist' % (rooturl, team_name))
    browser.getControl('Create new Mailing List').click()


def get_alternative_email(person):
    """Return a non-preferred IEmailAddress for a person.

    This assumes and asserts that there is exactly one non-preferred email
    address for the person.
    """
    alternatives = list(person.validatedemails)
    assert len(alternatives) == 1, (
        'Unexpected email count: %d' % len(alternatives))
    return alternatives[0]


def review_list(list_name, status=None):
    """Review a mailing list application.

    :param list_name: The name of the mailing list to review.  This is
        equivalent to the name of the team that the mailing list is
        associated with.
    :param status: The status applied to the reviewed mailing list.  This must
        be either MailingListStatus.APPROVED or MailingListStatus.DECLINED
        with the former being used if `status` is not given.
    """
    if status is None:
        status = MailingListStatus.APPROVED
    list_set = getUtility(IMailingListSet)
    return list_set.get(list_name)


class MailmanStub:
    """A stand-in for Mailman's XMLRPC client for page tests."""

    def act(self):
        """Perform the effects of the Mailman XMLRPC client.

        This doesn't have to be complete, it just has to do whatever the
        appropriate tests require.
        """
        # Simulate constructing and activating new mailing lists.
        mailing_list_set = getUtility(IMailingListSet)
        for mailing_list in mailing_list_set.approved_lists:
            mailing_list.startConstructing()
            mailing_list.transitionToStatus(MailingListStatus.ACTIVE)
        for mailing_list in mailing_list_set.deactivated_lists:
            mailing_list.transitionToStatus(MailingListStatus.INACTIVE)
        for mailing_list in mailing_list_set.modified_lists:
            mailing_list.startUpdating()
            mailing_list.transitionToStatus(MailingListStatus.ACTIVE)
        # Simulate acknowledging held messages.
        message_set = getUtility(IMessageApprovalSet)
        for status in (PostedMessageStatus.APPROVAL_PENDING,
                       PostedMessageStatus.REJECTION_PENDING,
                       PostedMessageStatus.DISCARD_PENDING):
            message_set.acknowledgeMessagesWithStatus(status)


mailman = MailmanStub()


class MailingListXMLRPCTestProxy(MailingListAPIView):
    """A low impedance test proxy for code that uses MailingListAPIView."""

    @fault_catcher
    def getPendingActions(self):
        return super(MailingListXMLRPCTestProxy, self).getPendingActions()

    @fault_catcher
    def reportStatus(self, statuses):
        return super(MailingListXMLRPCTestProxy, self).reportStatus(statuses)

    @fault_catcher
    def getMembershipInformation(self, teams):
        return super(
            MailingListXMLRPCTestProxy, self).getMembershipInformation(teams)

    @fault_catcher
    def isLaunchpadMember(self, address):
        return super(MailingListXMLRPCTestProxy, self).isLaunchpadMember(
            address)

    @fault_catcher
    def isTeamPublic(self, team_name):
        return super(MailingListXMLRPCTestProxy, self).isTeamPublic(team_name)
