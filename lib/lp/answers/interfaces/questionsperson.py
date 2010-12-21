# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

__metaclass__ = type
__all__ = [
    'IQuestionsPerson',
    ]


from lp.answers.interfaces.questioncollection import (
    IQuestionCollection,
    QUESTION_STATUS_DEFAULT_SEARCH,
    )


class IQuestionsPerson(IQuestionCollection):

    def getDirectAnswerQuestionTargets():
        """Return a list of IQuestionTargets that a person is subscribed to.

        This will return IQuestionTargets that the person is registered as an
        answer contact because he subscribed himself.
        """

    def getTeamAnswerQuestionTargets():
        """Return a list of IQuestionTargets that are indirect subscriptions.

        This will return IQuestionTargets that the person or team is
        registered as an answer contact because of his membership in a team.
        """

    def searchQuestions(search_text=None,
                        status=QUESTION_STATUS_DEFAULT_SEARCH,
                        language=None, sort=None, participation=None,
                        needs_attention=None):
        """Search the person's questions.

        See IQuestionCollection for the description of the standard search
        parameters.

        :participation: A list of QuestionParticipation that defines the set
        of relationship to questions that will be searched. If None or an
        empty sequence, all relationships are considered.

        :needs_attention: If this flag is true, only questions needing
        attention from the person will be included. Questions needing
        attention are those owned by the person in the ANSWERED or NEEDSINFO
        state, as well as, those not owned by the person but on which the
        person requested for more information or gave an answer and that are
        back in the OPEN state.
        """

