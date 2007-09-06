# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

"""Interfaces for a Question."""

__metaclass__ = type

__all__ = [
    'IQuestionCollection',
    'IQuestionSet',
    'ISearchableByQuestionOwner',
    'QUESTION_STATUS_DEFAULT_SEARCH'
    ]

from zope.interface import Interface, Attribute

from canonical.launchpad.interfaces.questionenums import QuestionStatus


QUESTION_STATUS_DEFAULT_SEARCH = (
    QuestionStatus.OPEN, QuestionStatus.NEEDSINFO, QuestionStatus.ANSWERED,
    QuestionStatus.SOLVED)


class IQuestionCollection(Interface):
    """An object that can be used to search through a collection of questions.
    """

    def searchQuestions(search_text=None,
                        status=QUESTION_STATUS_DEFAULT_SEARCH,
                        language=None, sort=None):
        """Return the questions from the collection matching search criteria.

        :search_text: A string that is matched against the question
        title and description. If None, the search_text is not included as
        a filter criteria.

        :status: A sequence of QuestionStatus Items. If None or an empty
        sequence, the status is not included as a filter criteria.

        :language: An ILanguage or a sequence of ILanguage objects to match
        against the question's language. If None or an empty sequence,
        the language is not included as a filter criteria.

        :sort:  An attribute of QuestionSort. If None, a default value is used.
        When there is a search_text value, the default is to sort by
        RELEVANCY, otherwise results are sorted NEWEST_FIRST.
        """

    def getQuestionLanguages():
        """Return the set of ILanguage used by all the questions in the
        collection."""


class ISearchableByQuestionOwner(IQuestionCollection):
    """Collection that support searching by question owner."""

    def searchQuestions(search_text=None,
                        status=QUESTION_STATUS_DEFAULT_SEARCH,
                        language=None, sort=None, owner=None,
                        needs_attention_from=None):
        """Return the questions from the collection matching search criteria.

        See `IQuestionCollection` for the description of the standard search
        parameters.

        :owner: The IPerson that created the question.

        :needs_attention_from: Selects questions that nee attention from an
        IPerson. These are the questions in the NEEDSINFO or ANSWERED state
        owned by the person. The questions not owned by the person but on
        which the person requested for more information or gave an answer
        and that are back in the OPEN state are also included.
        """


class IQuestionSet(IQuestionCollection):
    """A utility that contain all the questions published in Launchpad."""

    title = Attribute('Title')

    def get(question_id, default=None):
        """Return the question with the given id.

        Return :default: if no such question exists.
        """

    def findExpiredQuestions(days_before_expiration):
        """Return the questions that are expired.

        This should return all the questions in the Open or Needs information
        state, without an assignee, that didn't receive any new comments in
        the last <days_before_expiration> days.
        """

    def getMostActiveProjects(limit=5):
        """Return the list of projects that asked the most questions in
        the last 60 days.

        It should only return projects that officially uses the Answer
        Tracker.

        :param limit: The number of projects to return.
        """
