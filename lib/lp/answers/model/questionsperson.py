# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'QuestionsPerson',
    ]


from zope.component import adapts
from zope.interface import implements

from canonical.database.sqlbase import sqlvalues
from lp.answers.interfaces.questioncollection import (
    QUESTION_STATUS_DEFAULT_SEARCH,
    )
from lp.answers.interfaces.questionsperson import IQuestionsPerson
from lp.answers.model.answercontact import AnswerContact
from lp.answers.model.question import QuestionPersonSearch
from lp.registry.interfaces.person import IPerson
from lp.services.worlddata.model.language import Language


class QuestionsPerson:
    """See `IQuestionsPerson`."""
    implements(IQuestionsPerson)
    adapts(IPerson)

    def __init__(self, person):
        self.person = person

    def searchQuestions(self, search_text=None,
                        status=QUESTION_STATUS_DEFAULT_SEARCH,
                        language=None, sort=None, participation=None,
                        needs_attention=None):
        """See `IQuestionsPerson`."""
        return QuestionPersonSearch(
                person=self.person,
                search_text=search_text,
                status=status, language=language, sort=sort,
                participation=participation,
                needs_attention=needs_attention
                ).getResults()

    def getQuestionLanguages(self):
        """See `IQuestionCollection`."""
        return set(Language.select(
            """Language.id = language AND Question.id IN (
            SELECT id FROM Question
                      WHERE owner = %(personID)s OR answerer = %(personID)s OR
                           assignee = %(personID)s
            UNION SELECT question FROM QuestionSubscription
                  WHERE person = %(personID)s
            UNION SELECT question
                  FROM QuestionMessage JOIN Message ON (message = Message.id)
                  WHERE owner = %(personID)s
            )""" % sqlvalues(personID=self.person.id),
            clauseTables=['Question'], distinct=True))

    def getDirectAnswerQuestionTargets(self):
        """See `IQuestionsPerson`."""
        answer_contacts = AnswerContact.select(
            'person = %s' % sqlvalues(self.person))
        return self._getQuestionTargetsFromAnswerContacts(answer_contacts)

    def getTeamAnswerQuestionTargets(self):
        """See `IQuestionsPerson`."""
        answer_contacts = AnswerContact.select(
            '''AnswerContact.person = TeamParticipation.team
            AND TeamParticipation.person = %(personID)s
            AND AnswerContact.person != %(personID)s''' % sqlvalues(
                personID=self.person.id),
            clauseTables=['TeamParticipation'], distinct=True)
        return self._getQuestionTargetsFromAnswerContacts(answer_contacts)

    def _getQuestionTargetsFromAnswerContacts(self, answer_contacts):
        """Return a list of active IQuestionTargets.

        :param answer_contacts: an iterable of `AnswerContact`s.
        :return: a list of active `IQuestionTarget`s.
        :raise AssertionError: if the IQuestionTarget is not a `Product`,
            `Distribution`, or `SourcePackage`.
        """
        targets = set()
        for answer_contact in answer_contacts:
            if answer_contact.product is not None:
                target = answer_contact.product
                pillar = target
            elif answer_contact.sourcepackagename is not None:
                assert answer_contact.distribution is not None, (
                    "Missing distribution.")
                distribution = answer_contact.distribution
                target = distribution.getSourcePackage(
                    answer_contact.sourcepackagename)
                pillar = distribution
            elif answer_contact.distribution is not None:
                target = answer_contact.distribution
                pillar = target
            else:
                raise AssertionError('Unknown IQuestionTarget.')

            if pillar.active:
                # Deactivated pillars are not valid IQuestionTargets.
                targets.add(target)

        return list(targets)
