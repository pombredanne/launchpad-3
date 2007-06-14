# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper functions for Answer Tracker tests."""

__metaclass__ = type
__all__ = [
    'QuestionFactory'
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    ILaunchBag, IQuestionTarget, IPillarNameSet)


class QuestionFactory:
    """Helper object that can be used to quickly create questions."""

    @classmethod
    def _getQuestionTarget(cls, target_or_name):
        """Return the `IQuestionTarget` to use for target_or_name.

        If target_or_name provides `IQuestionTarget` it is returned,
        otherwise if it is a string a project with that name is looked up.
        """
        if isinstance(target_or_name, basestring):
            target = getUtility(IPillarNameSet).getByName(target_or_name)
            assert target is not None, (
                'No project with name %s' % target_or_name)
        else:
            target = IQuestionTarget(target_or_name)
        assert IQuestionTarget.providedBy(target), (
            "%r doesn't provide IQuestionTarget" % target)
        return target

    @classmethod
    def createManyByProject(cls, specification):
        """Create a number of questions on selected projects.

        The function expects a list of list of the form
        [project, question_count].

        Project can be an object providing `IQuestionTarget` or a string which
        will be used to look up the project by name.
    
        question_count is the number of questions to create on the project.

        Question are created by the logged in user.
        """
        owner = getUtility(ILaunchBag).user
        for project, question_count in specification:
            target = cls._getQuestionTarget(project)
            for index in range(question_count):
                replacements = {'index' : index, 'target': target.displayname}
                target.newQuestion(
                    owner,
                    'Question %(index)s on %(target)s' % replacements,
                    'Description %(index)s on %(target)s' % replacements)
