# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'QuestionRecipientReason',
    ]

from lp.services.mail.basemailer import RecipientReason


class QuestionRecipientReason(RecipientReason):

    @classmethod
    def forSubscriber(cls, subscriber, recipient):
        header = cls.makeRationale("Subscriber", subscriber)
        reason = (
            "You received this question notification because "
            "%(lc_entity_is)s subscribed to the question.")
        return cls(subscriber, recipient, header, reason)

    @classmethod
    def forAsker(cls, asker, recipient):
        header = cls.makeRationale("Asker", asker)
        reason = (
            "You received this question notification because you asked the "
            "question.")
        return cls(asker, recipient, header, reason)

    @classmethod
    def forAssignee(cls, assignee, recipient):
        header = cls.makeRationale("Assignee", assignee)
        reason = (
            "You received this question notification because "
            "%(lc_entity_is)s assigned to this question.")
        return cls(assignee, recipient, header, reason)

    @classmethod
    def forAnswerContact(cls, answer_contact, recipient, target_name,
                         target_displayname):
        header = cls.makeRationale(
            "Answer Contact (%s)" % target_name, answer_contact)
        reason = (
            "You received this question notification because "
            "%%(lc_entity_is)s an answer contact for %s." % target_displayname)
        return cls(answer_contact, recipient, header, reason)
