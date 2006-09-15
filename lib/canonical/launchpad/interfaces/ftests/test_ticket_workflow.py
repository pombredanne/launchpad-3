# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test the ticket workflow methods.

Comprehensive tests for the ticket workflow methods. A narrative kind of
documentation is done in the ../../doc/support-tracker-workflow.txt Doctest,
but testing all the possible transitions makes the documentation more heavy
than necessary. This is tested here.
"""

__metaclass__ = type

__all__ = []

from datetime import datetime, timedelta
from pytz import UTC
import unittest

from zope.component import getUtility
from zope.interface.verify import verifyObject
from zope.security.interfaces import Unauthorized

from canonical.launchpad.interfaces import (
    IDistributionSet, IPersonSet, ITicketMessage)
from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.lp.dbschema import TicketAction, TicketStatus
from canonical.testing.layers import LaunchpadFunctionalLayer

class SupportTrackerWorkflowTestCase(unittest.TestCase):
    """Test the ITicket workflow methods.

    This ensure that all possible transitions work correctly and
    that all invalid transitions are reported.
    """

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        self.now = datetime.now(UTC)

        # Workflow methods are available only to logged in user
        login('no-priv@canonical.com')

        # Set up actors
        personset = getUtility(IPersonSet)
        # User who submits request
        self.no_priv = personset.getByEmail('no-priv@canonical.com')
        # User who answers request
        self.sample_person = personset.getByEmail('test@canonical.com')

        # Admin user which can change ticket status
        self.foo_bar = personset.getByEmail('foo.bar@canonical.com')

        # Simple ubuntu ticket
        self.ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        self.ticket = self.ubuntu.newTicket(
            self.no_priv, 'Help!', 'I need help with Ubuntu',
            datecreated=self.now)

    def now_plus(self, n_hours):
        """Return a DateTime a number of hours in the future."""
        return self.now + timedelta(hours=n_hours)

    def testWorkflowMethodsPermission(self):
        """Verify the workflow methods permission.

        Only a logged in user can access the workflow methods.
        """
        workflow_methods = (
            'requestInfo', 'giveInfo', 'giveAnswer', 'confirmAnswer',
            'expireTicket', 'reject')
        login(ANONYMOUS)
        for method in workflow_methods:
            try:
                getattr(self.ticket, method)
                self.fail(
                    "Method %s should not be accessible by the anonymous "
                    "user." % method)
            except Unauthorized:
                pass

        login('no-priv@canonical.com')
        for method in workflow_methods:
            self.failUnless(getattr, getattr(self.ticket, method))

    def test_can_request_info(self):
        """Test the can_request_info attribute in all the possible states."""
        self._testTransitionGuard(
            'can_request_info', ['OPEN', 'NEEDSINFO', 'ANSWERED'])

    def test_requestInfo(self):
        """Test that requestInfo() can be called in the OPEN, NEEDSINFO,
        and ANSWERED state and that it returns a valid ITicketMessage.
        """
        self._testValidTransition(
            [TicketStatus.OPEN, TicketStatus.NEEDSINFO],
            expected_owner=self.sample_person,
            expected_action=TicketAction.REQUESTINFO,
            expected_status=TicketStatus.NEEDSINFO,
            transition_method=self.ticket.requestInfo,
            transition_method_args=(
                self.sample_person, "What's your problem?"))

        # Even if the ticket is answered, a user can request more
        # information, but that leave the ticket in the ANSWERED state.
        self.ticket.setStatus(
            self.foo_bar, TicketStatus.ANSWERED, 'Status change')
        message = self.ticket.requestInfo(
            self.sample_person,
            "The previous answer is bad. What is the problem again?",
            datecreated=self.now_plus(3))
        self.checkTransitionMessage(
            message, expected_owner=self.sample_person,
            expected_action=TicketAction.REQUESTINFO,
            expected_status=TicketStatus.ANSWERED)

    def test_requestInfoFromOwnerIsInvalid(self):
        """Test that the ticket owner cannot use requestInfo."""
        self.assertRaises(
            AssertionError, self.ticket.requestInfo,
                self.no_priv, 'Why should I care?',
                datecreated=self.now_plus(1))

    def test_requestInfoFromInvalidStates(self):
        """Test that requestInfo cannot be called when the ticket status is
        not OPEN or NEEDSINFO.
        """
        self._testInvalidTransition(
            ['OPEN', 'NEEDSINFO', 'ANSWERED'], self.ticket.requestInfo,
            self.sample_person, "What's up?", datecreated=self.now_plus(3))

    def test_can_give_info(self):
        """Test the can_give_info attribute in all the possible states."""
        self._testTransitionGuard('can_give_info', ['OPEN', 'NEEDSINFO'])

    def test_giveInfoFromInvalidStates(self):
        """Test that giveInfo cannot be called when the ticket status is
        not OPEN or NEEDSINFO.
        """
        self._testInvalidTransition(
            ['OPEN', 'NEEDSINFO'], self.ticket.giveInfo,
            "That's that.", datecreated=self.now_plus(1))

    def test_giveInfo(self):
        """Test that giveInfo() can be called when the ticket status is
        OPEN or NEEDSINFO and that it returns a valid ITicketMessage.
        """
        self._testValidTransition(
            [TicketStatus.OPEN, TicketStatus.NEEDSINFO],
            expected_owner=self.no_priv,
            expected_action=TicketAction.GIVEINFO,
            expected_status=TicketStatus.OPEN,
            transition_method=self.ticket.giveInfo,
            transition_method_args=("That's that.",))

    def test_can_give_answer(self):
        """Test the can_give_answer attribute in all the possible states."""
        self._testTransitionGuard(
            'can_give_answer', ['OPEN', 'NEEDSINFO', 'ANSWERED'])

    def test_giveAnswerFromInvalidStates(self):
        """Test that giveAnswer cannot be called when the ticket status is
        is not OPEN, NEEDSINFO, or ANSWERED.
        """
        self._testInvalidTransition(
            ['OPEN', 'NEEDSINFO', 'ANSWERED'], self.ticket.giveAnswer,
            self.sample_person, "The answer is this.",
            datecreated=self.now_plus(1))

    def test_giveAnswer(self):
        """Test that giveAnswer can be called when the ticket status is
        one of OPEN, NEEDSINFO or ANSWERED and check that it returns a
        valid ITicketMessage.
        """
        self._testValidTransition(
            [TicketStatus.OPEN, TicketStatus.NEEDSINFO,
             TicketStatus.ANSWERED],
            expected_owner=self.sample_person,
            expected_action=TicketAction.ANSWER,
            expected_status=TicketStatus.ANSWERED,
            transition_method=self.ticket.giveAnswer,
            transition_method_args=(
                self.sample_person, "It looks like a real problem.",))

        # When the owner gives the answer, the ticket moves straight to
        # ANSWERED_CONFIRMED
        def checkAnswerMessage(message):
            """Check the attributes that are set when an answer is
            confirmed.
            """
            self.assertEquals(message, self.ticket.answer)
            self.assertEquals(self.no_priv, self.ticket.answerer)
            self.assertEquals(message.datecreated, self.ticket.dateanswered)

        self._testValidTransition(
            [TicketStatus.OPEN, TicketStatus.NEEDSINFO,
             TicketStatus.ANSWERED],
            expected_owner=self.no_priv,
            expected_action=TicketAction.CONFIRM,
            expected_status=TicketStatus.ANSWERED_CONFIRMED,
            extra_message_check=checkAnswerMessage,
            transition_method=self.ticket.giveAnswer,
            transition_method_args=(
                self.no_priv, "I found the solution.",),
            transition_method_kwargs={'datecreated': self.now_plus(3)})

    def test_can_confirm_answer(self):
        """Test the can_confirm_answer attribute in all the possible states.
        """
        # When the ticket didn't receive an answer, it should always be
        # false
        self._testTransitionGuard('can_confirm_answer', [])

        # Once one answer was given, it becomes possible in some states
        self.ticket.setStatus(
            self.foo_bar, TicketStatus.OPEN, 'Status change')
        self.ticket.giveAnswer(
            self.sample_person, 'Do something about it.', self.now_plus(1))
        self._testTransitionGuard(
            'can_confirm_answer', ['OPEN', 'NEEDSINFO', 'ANSWERED'])

    def test_confirmAnswerFromInvalidStates(self):
        """Test that confirmAnswer cannot be called when the ticket has
        no message with action ANSWER, or when it has one but it is not in the
        OPEN, NEEDSINFO or ANSWERED state.
        """
        self._testInvalidTransition([], self.ticket.confirmAnswer,
            "That answer worked!.", datecreated=self.now_plus(1))

        self.ticket.setStatus(
            self.foo_bar, TicketStatus.OPEN, 'Status change')
        answer_message = self.ticket.giveAnswer(
            self.sample_person, 'Do something about it.', self.now_plus(1))
        self._testInvalidTransition(['OPEN', 'NEEDSINFO', 'ANSWERED'],
            self.ticket.confirmAnswer, "That answer worked!.",
            answer=answer_message, datecreated=self.now_plus(1))

    def test_confirmAnswer(self):
        """Test that confirmAnswer can be called when the ticket status
        is one of OPEN, NEEDSINFO, ANSWERED and that it has at least one
        ANSWER message and check that it returns a valid ITicketMessage.
        """
        answer_message = self.ticket.giveAnswer(
            self.sample_person, "Get a grip!", datecreated=self.now_plus(1))

        def checkAnswerMessage(message):
            """Check the attributes that are set when an answer is
            confirmed.
            """
            self.assertEquals(answer_message, self.ticket.answer)
            self.assertEquals(self.sample_person, self.ticket.answerer)
            self.assertEquals(message.datecreated, self.ticket.dateanswered)
        self._testValidTransition(
            [TicketStatus.OPEN, TicketStatus.NEEDSINFO,
             TicketStatus.ANSWERED],
            expected_owner=self.no_priv,
            expected_action=TicketAction.CONFIRM,
            expected_status=TicketStatus.ANSWERED_CONFIRMED,
            extra_message_check=checkAnswerMessage,
            transition_method=self.ticket.confirmAnswer,
            transition_method_args=("That was very useful.",),
            transition_method_kwargs={'answer': answer_message})

    def testCannotConfirmAnAnswerFromAnotherTicket(self):
        """Test that you can't confirm an answer not from the same ticket."""
        ticket1_answer = self.ticket.giveAnswer(
            self.sample_person, 'Really, just do it!')
        ticket2 = self.ubuntu.newTicket(self.no_priv, 'Help 2', 'Help me!')
        ticket2_answer = ticket2.giveAnswer(
            self.sample_person, 'Do that!')
        answerRefused = False
        try:
            ticket2.confirmAnswer('That worked!', answer=ticket1_answer)
        except AssertionError:
            answerRefused = True
        self.failUnless(
            answerRefused, 'confirmAnswer accepted a message from a different'
            'ticket')

    def test_can_reopen(self):
        """Test the can_reopen attribute in all the possible states."""
        self._testTransitionGuard('can_reopen', ['ANSWERED', 'EXPIRED'])

    def test_reopenFromInvalidStates(self):
        """Test that reopen cannot be called when the ticket status is
        not one of OPEN, NEEDSINFO, or ANSWERED.
        """
        self._testInvalidTransition(
            ['ANSWERED', 'EXPIRED'], self.ticket.reopen,
            "I still have a problem.", datecreated=self.now_plus(1))

    def test_reopen(self):
        """Test that reopen() can be called when the ticket is in the
        ANSWERED and EXPIRED state and that it returns a valid
        ITicketMessage.
        """
        self._testValidTransition(
            [TicketStatus.ANSWERED, TicketStatus.EXPIRED],
            expected_owner=self.no_priv,
            expected_action=TicketAction.REOPEN,
            expected_status=TicketStatus.OPEN,
            transition_method=self.ticket.reopen,
            transition_method_args=('I still have this problem.',))

    def test_expireTicketFromInvalidStates(self):
        """Test that expireTicket cannot be called when the ticket status is
        not one of OPEN or NEEDSINFO.
        """
        self._testInvalidTransition(
            ['OPEN', 'NEEDSINFO'], self.ticket.expireTicket,
            self.sample_person, "Too late.", datecreated=self.now_plus(1))

    def test_expireTicket(self):
        """Test that expireTicket() can be called when the ticket status is
        OPEN or NEEDSINFO and that it returns a valid ITicketMessage.
        """
        self._testValidTransition(
            [TicketStatus.OPEN, TicketStatus.NEEDSINFO],
            expected_owner=self.sample_person,
            expected_action=TicketAction.EXPIRE,
            expected_status=TicketStatus.EXPIRED,
            transition_method=self.ticket.expireTicket,
            transition_method_args=(
                self.sample_person, 'This ticket is expired.'))

    def test_rejectFromInvalidStates(self):
        """Test that expireTicket cannot be called when the ticket status is
        not one of OPEN or NEEDSINFO.
        """
        valid_statuses = [status.name for status in TicketStatus.items
                          if status.name != 'INVALID']
        # Reject user must be a support contact, (or admin, or product owner)
        self.ubuntu.addSupportContact(self.sample_person)
        self._testInvalidTransition(
            valid_statuses, self.ticket.reject,
            self.sample_person, "This is lame.", datecreated=self.now_plus(1))

    def test_reject(self):
        """Test that expireTicket() can be called when the ticket status is
        OPEN or NEEDSINFO and that it returns a valid ITicketMessage.
        """
        # Reject user must be a support contact, (or admin, or product owner)
        self.ubuntu.addSupportContact(self.sample_person)
        valid_statuses = [status for status in TicketStatus.items
                          if status.name != 'INVALID']
        self._testValidTransition(
            valid_statuses,
            expected_owner=self.sample_person,
            expected_action=TicketAction.REJECT,
            expected_status=TicketStatus.INVALID,
            transition_method=self.ticket.reject,
            transition_method_args=(
                self.sample_person, 'This is lame.'))

    def testDisallowNoOpSetStatus(self):
        """Test that calling setStatus to change to the same status
        raises an AssertionError.
        """
        exceptionRaised = False
        try:
            self.ticket.setStatus(
                self.foo_bar, TicketStatus.OPEN, 'Status Change')
        except AssertionError:
            exceptionRaised = True
        self.failUnless(exceptionRaised,
                        "setStatus() to same status should raise an error")

    def _testTransitionGuard(self, guard_name, statuses_expected_true):
        """Helper that verifies that the Ticket guard_name attribute
        is True when the ticket status is one listed in statuses_expected_true
        and False otherwise.
        """
        for status in TicketStatus.items:
            if status != self.ticket.status:
                self.ticket.setStatus(
                    self.foo_bar, status, 'Status change')
            expected = status.name in statuses_expected_true
            allowed = getattr(self.ticket, guard_name)
            self.failUnless(
                expected == allowed, "%s != %s when status = %s" % (
                    guard_name, expected, status.name))

    def _testValidTransition(self, statuses, transition_method,
                            expected_owner, expected_action, expected_status,
                            extra_message_check=None,
                            transition_method_args=(),
                            transition_method_kwargs=None):
        """Helper that verifies that transition_method can be called when
        the ticket status is one listed in statuses. It will validate the
        returned message using checkTransitionMessage. The transition_method
        is called with the transition_method_args as positional parameters
        and transition_method_kwargs as keyword parameters.

        If extra_message_check is passed a function, it will be called with
        the returned message for extra checks.

        The datecreated parameter to the transition_method is set
        automatically to a value that will make the message sort last.
        """
        count=0
        if transition_method_kwargs is None:
            transition_method_kwargs = {}
        if 'datecreated' not in transition_method_kwargs:
            transition_method_kwargs['datecreated'] = self.now_plus(0)
        for status in statuses:
            if status != self.ticket.status:
                self.ticket.setStatus(
                    self.foo_bar, status, 'Status change')
            # Ensure ordering of the message
            transition_method_kwargs['datecreated'] = (
                transition_method_kwargs['datecreated'] + timedelta(hours=1))
            message = transition_method(*transition_method_args,
                                        **transition_method_kwargs)
            try:
                self.checkTransitionMessage(
                    message, expected_owner=expected_owner,
                    expected_action=expected_action,
                    expected_status=expected_status)
                if extra_message_check:
                    extra_message_check(message)
            except AssertionError, e:
                raise AssertionError, (
                    "Failure in validating message returned by %s when "
                    "status %s: %s" % (
                        transition_method.__name__, status.name, e))
            count += 1

    def _testInvalidTransition(self, valid_statuses, transition_method,
                               *args, **kwargs):
        """Helper that verifies that transition_method method cannot be
        called when the ticket status is different than the ones in
        valid_statuses.

        args and kwargs contains the parameters that should be passed to the
        transition method.
        """
        for status in TicketStatus.items:
            if status.name in valid_statuses:
                continue
            exceptionRaised = False
            try:
                if status != self.ticket.status:
                    self.ticket.setStatus(
                        self.foo_bar, status, 'Status change')
                transition_method(*args, **kwargs)
            except AssertionError:
                exceptionRaised = True
            self.failUnless(exceptionRaised,
                            "%s() when status = %s should raise an error" % (
                                transition_method.__name__, status.name))

    def checkTransitionMessage(self, message, expected_owner,
                               expected_action, expected_status):
        """Helper method to check the message created by a transition.

        It make sure that the message provides ITicketMessage and that it
        was appended to the ticket messages attribute. It also checks that
        the subject was computed correctly and that the newstatus, action
        and owner attributes were set correctly.

        It also verifies that the ticket status, datelastquery (or
        datelastresponse) were updated to reflect the time of the message.
        """
        self.failUnless(verifyObject(ITicketMessage, message))

        self.assertEquals("Re: Help!", message.subject)
        self.assertEquals(expected_owner, message.owner)
        self.assertEquals(expected_action, message.action)
        self.assertEquals(expected_status, message.newstatus)

        self.assertEquals(message, self.ticket.messages[-1])
        self.assertEquals(expected_status, self.ticket.status)

        if expected_owner == self.ticket.owner:
            self.assertEquals(message.datecreated, self.ticket.datelastquery)
        else:
            self.assertEquals(
                message.datecreated, self.ticket.datelastresponse)


def test_suite():
    return unittest.makeSuite(SupportTrackerWorkflowTestCase)

if __name__ == '__main__':
    unittest.main()
