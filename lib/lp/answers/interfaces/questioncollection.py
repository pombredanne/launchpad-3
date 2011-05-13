# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Interfaces for a Question."""

__metaclass__ = type

__all__ = [
    'IQuestionCollection',
    'IQuestionSet',
    'ISearchableByQuestionOwner',
    ]

from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Choice,
    Int,
    List,
    TextLine,
    )

from lazr.restful.declarations import (
    collection_default_content,
    export_as_webservice_collection,
    export_operation_as,
    export_read_operation,
    operation_for_version,
    operation_parameters,
    operation_returns_collection_of,
    operation_returns_entry,
    )

from canonical.launchpad import _
from lp.answers.enums import (
    QUESTION_STATUS_DEFAULT_SEARCH,
    QuestionSort,
    QuestionStatus,
    )
from lp.services.fields import PublicPersonChoice


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

        :sort: An attribute of QuestionSort. If None, a default value is used.
        When there is a search_text value, the default is to sort by
        RELEVANCY, otherwise results are sorted NEWEST_FIRST.
        """

    def getQuestionLanguages():
        """Return the set of ILanguage used by all the questions in the
        collection."""


class ISearchableByQuestionOwner(IQuestionCollection):
    """Collection that support searching by question owner."""

    @operation_parameters(
        search_text=TextLine(
            title=_('Search text'),
            description=_(
                "Optional text that is in the text of the questions."),
            required=False),
#        status=List(
#            title=_('Status'),
#            description=_(
#                'An optional list of statuses the questions may be'),
#            value_type=Choice(vocabulary=QuestionStatus), required=False),
        language=List(
            title=_('Language'),
            description=_(
                'An optional list of languages the questions are in.'),
            value_type=Choice(vocabulary='Language'), required=False),
#        sort=Choice(
#            title=_('Sort'),
#            description=_('The optional method to sort the questions by'),
#            vocabulary=QuestionSort, required=False),
        owner=PublicPersonChoice(
            title=_('Owner'),
            description=_('The optional user that asked the question.'),
            vocabulary='ValidPerson', required=False),
        needs_attention_from=PublicPersonChoice(
            title=_('Needs attentions from'),
            description=_(
                'The optional user with questions that need attention.'),
            vocabulary='ValidPerson', required=False))
    @operation_returns_collection_of(Interface)
    @export_read_operation()
    @operation_for_version('devel')
    def searchQuestions(search_text=None,
                        status=QUESTION_STATUS_DEFAULT_SEARCH,
                        language=None, sort=None, owner=None,
                        needs_attention_from=None):
        """Return the questions from the collection matching search criteria.

        See `IQuestionCollection` for the description of the standard search
        parameters.

        :param owner: The IPerson that created the question.

        :param needs_attention_from: Selects questions that need attention
            from an IPerson. These are the questions in the NEEDSINFO or
            ANSWERED state owned by the person. The questions not owned by the
            person but on which the person requested more information or gave
            an answer and that are back in the OPEN state are also included.
        """


class IQuestionSet(IQuestionCollection):
    """A utility that contain all the questions published in Launchpad."""

    export_as_webservice_collection(Interface)

    title = Attribute('Title')

    @operation_parameters(
        question_id=Int(
            title=_('The id of the question to get'),
            required=True))
    @operation_returns_entry(Interface)
    @export_read_operation()
    @export_operation_as("getByID")
    @operation_for_version('devel')
    def get(question_id, default=None):
        """Return the question with the given id.

        Return :default: if no such question exists.
        """

    def findExpiredQuestions(days_before_expiration):
        """Return the questions that are expired.

        Return all the questions in the Open or Needs information state,
        without an assignee or bug links, that did not receive any new
        comments in the last <days_before_expiration> days.
        """

    @collection_default_content(limit=5)
    def getMostActiveProjects(limit=5):
        """Return the list of projects that asked the most questions in
        the last 60 days.

        It should only return projects that officially uses the Answer
        Tracker.

        :param limit: The number of projects to return.
        """

    def getOpenQuestionCountByPackages(packages):
        """Return number of open questions for the list of packages.

        :param packages: A list of `IDistributionSourcePackage`
            instances.

        :return: a dictionary, where the package is the key, and the
            number of open questions the value.
        """
