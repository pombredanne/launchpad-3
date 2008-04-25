# Copyright 2007-2008 Canonical Ltd.  All rights reserved.

"""Helper functions for testing XML-RPC services."""

__metaclass__ = type
__all__ = [
    'apply_for_list',
    'fault_catcher',
    'get_alternative_email',
    'mailman',
    'new_person',
    'new_team',
    'print_actions',
    'print_info',
    'print_review_table',
    'review_list',
    ]


import re
import xmlrpclib

from BeautifulSoup import BeautifulSoup, SoupStrainer
from zope.component import getUtility

from canonical.database.sqlbase import flush_database_updates
from canonical.config import config
from canonical.launchpad.ftests import login, logout
from canonical.launchpad.interfaces import (
    EmailAddressStatus, IEmailAddressSet, ILaunchpadCelebrities,
    IMailingListSet, IPersonSet, MailingListAutoSubscribePolicy,
    MailingListStatus, PersonCreationRationale, TeamSubscriptionPolicy)


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


def print_info(info):
    """A helper function for the mailing list tests.

    This prints the results of the XMLRPC .getPendingActions() call.

    Note that in order to make the tests that use this method a little
    clearer, we specifically suppress printing of the mail-archive recipient.
    You should pick the info apart manually if you want that.
    """
    for team_name in sorted(info):
        print team_name
        subscribees = info[team_name]
        for address, realname, flags, status in subscribees:
            if (config.mailman.archive_address and
                address == config.mailman.archive_address):
                # Don't print this information
                pass
            else:
                print '    %-23s' % address, realname, flags, status


def print_review_table(content):
    """Print a +mailinglists table in a nice format."""
    table = BeautifulSoup(
        content,
        parseOnlyThese=SoupStrainer(attrs=dict(id='mailing-lists')))
    for tr in table.findAll('tr'):
        for index, thtd in enumerate(tr.findAll(['th', 'td'])):
            if thtd.name == 'th':
                # This is a heading.  To enable the page test to keep
                # everything on one line with no wrapping, we'll abbreviate
                # the first three headings.
                if index < 3:
                    print thtd.string[:3],
                else:
                    print thtd.string,
            else:
                # Either there's a radio button here, or a team name, or a
                # person name.  In the former two cases, print a
                # representation of whether the button is checked or not.  In
                # the latter two cases, just print the text.
                if thtd.input is None:
                    text = re.sub(u'&nbsp;', ' ', thtd.a.contents[1])
                    print '%s <%s>' % (text, thtd.a.get('href')),
                else:
                    if thtd.input.get('checked', None):
                        print '(*)',
                    else:
                        print '( )',
        print


def new_team(team_name, with_list=False):
    """A helper function for the mailinglist doctests.

    This just provides a convenience function for creating the kinds of teams
    we need to use in the doctest.
    """
    displayname = ' '.join(word.capitalize() for word in team_name.split('-'))
    # XXX BarryWarsaw Set the team's subscription policy to OPEN because of
    # bug 125505.
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
    experts = getUtility(ILaunchpadCelebrities).mailing_list_experts
    reviewer = list(experts.allmembers)[0]
    list_set = getUtility(IMailingListSet)
    team_list = list_set.new(team)
    team_list.review(reviewer, MailingListStatus.APPROVED)
    team_list.startConstructing()
    team_list.transitionToStatus(MailingListStatus.ACTIVE)
    flush_database_updates()
    return team_list


def apply_for_list(browser, team_name):
    """Create a team and apply for its mailing list.

    This should only be used in page tests.
    """
    displayname = ' '.join(word.capitalize() for word in team_name.split('-'))
    browser.open('http://launchpad.dev/people/+newteam')
    browser.getControl(name='field.name').value = team_name
    browser.getControl('Display Name').value = displayname
    # Use an open team for simplicity.
    browser.getControl(
        name='field.subscriptionpolicy').displayValue = ['Open Team']
    browser.getControl('Create').click()
    # Apply for the team's mailing list'
    browser.open('http://launchpad.dev/~%s' % team_name)
    browser.getLink('Configure mailing list').click()
    browser.getControl('Apply for Mailing List').click()


def new_person(first_name, set_preferred_email=True,
               use_default_autosubscribe_policy=False):
    """Create a new person with the given first name.

    The person will be given two email addresses, with the 'long form'
    (e.g. anne.person@example.com) as the preferred address.  Return the new
    person object.
    """
    variable_name = first_name.lower()
    full_name = first_name + ' Person'
    # E.g. firstname.person@example.com will be an alternative address.
    preferred_address = variable_name + '.person@example.com'
    # E.g. aperson@example.org will be the preferred address.
    alternative_address = variable_name[0] + 'person@example.org'
    person, email = getUtility(IPersonSet).createPersonAndEmail(
        preferred_address,
        PersonCreationRationale.OWNER_CREATED_LAUNCHPAD,
        name=variable_name, displayname=full_name)
    if set_preferred_email:
        person.setPreferredEmail(email)

    if not use_default_autosubscribe_policy:
        # Shut off list auto-subscription so that we have direct control
        # over subscriptions in the doctests.
        person.mailing_list_auto_subscribe_policy = \
            MailingListAutoSubscribePolicy.NEVER
    getUtility(IEmailAddressSet).new(alternative_address, person,
                                     EmailAddressStatus.VALIDATED)
    return person


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
    # Any Mailing List Expert will suffice for approving the registration.
    experts = getUtility(ILaunchpadCelebrities).mailing_list_experts
    lpadmin = list(experts.allmembers)[0]
    # Review and approve the mailing list registration.
    list_set = getUtility(IMailingListSet)
    mailing_list = list_set.get(list_name)
    mailing_list.review(lpadmin, status)


class MailmanStub:
    """A stand-in for Mailman's XMLRPC client for page tests."""

    def act(self):
        """Perform the effects of the Mailman XMLRPC client."""
        # This doesn't have to be complete.
        login('foo.bar@canonical.com')
        mailing_list_set = getUtility(IMailingListSet)
        for mailing_list in mailing_list_set.approved_lists:
            mailing_list.startConstructing()
            mailing_list.transitionToStatus(MailingListStatus.ACTIVE)
        logout()
        flush_database_updates()


mailman = MailmanStub()
