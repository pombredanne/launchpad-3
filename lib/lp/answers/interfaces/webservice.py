# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""All the interfaces that are exposed through the webservice.

There is a declaration in ZCML somewhere that looks like:
  <webservice:register module="lp.answers.interfaces.webservice" />

which tells `lazr.restful` that it should look for webservice exports here.
"""

__all__ = [
    'IFAQ',
    'IFAQTarget',
    'IQuestion',
    'IQuestionMessage',
    'IQuestionSet',
    'IQuestionSubscription',
    'IQuestionTarget',
    ]

from lazr.restful.declarations import LAZR_WEBSERVICE_EXPORTED

from lp.answers.interfaces.faq import IFAQ
from lp.answers.interfaces.faqtarget import IFAQTarget
from lp.answers.interfaces.question import IQuestion
from lp.answers.interfaces.questioncollection import (
    IQuestionCollection,
    IQuestionSet,
    ISearchableByQuestionOwner,
    )
from lp.answers.interfaces.questionmessage import IQuestionMessage
from lp.answers.interfaces.questionsperson import IQuestionsPerson
from lp.answers.interfaces.questionsubscription import IQuestionSubscription
from lp.answers.interfaces.questiontarget import IQuestionTarget
from lp.services.webservice.apihelpers import (
    patch_collection_return_type,
    patch_entry_return_type,
    patch_reference_property,
    )


IQuestionSet.queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['collection_entry_schema'] = IQuestion
patch_entry_return_type(IQuestionSet, 'get', IQuestion)
patch_collection_return_type(
    IQuestionTarget, 'findSimilarQuestions', IQuestion)
patch_collection_return_type(
    IQuestionCollection, 'searchQuestions', IQuestion)
patch_collection_return_type(
    ISearchableByQuestionOwner, 'searchQuestions', IQuestion)
patch_reference_property(IQuestionMessage, 'question', IQuestion)
patch_reference_property(IQuestionSubscription, 'question', IQuestion)
patch_collection_return_type(
    IQuestionsPerson, 'getDirectAnswerQuestionTargets', IQuestionTarget)
patch_collection_return_type(
    IQuestionsPerson, 'getTeamAnswerQuestionTargets', IQuestionTarget)
patch_collection_return_type(
    IQuestionsPerson, 'searchQuestions', IQuestion)
