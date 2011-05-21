# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'AddAnswerContactError',
    'InvalidQuestionStateError',
    'NotAnswerContactError',
    'NotQuestionOwnerError',
    ]

import httplib

from lazr.restful.declarations import webservice_error


class AddAnswerContactError(ValueError):
    """The person cannot be an answer contact.

    An answer contacts must be a valid user or team that has a preferred
    language.
    """
    webservice_error(httplib.BAD_REQUEST)


class NotAnswerContactError(ValueError):
    """The person must be an answer contact."""
    webservice_error(httplib.BAD_REQUEST)


class NotQuestionOwnerError(ValueError):
    """The person be the the question owner."""
    webservice_error(httplib.BAD_REQUEST)


class InvalidQuestionStateError(Exception):
    """Error raised when the question is in an invalid state.

    Error raised when a workflow action cannot be executed because the
    question would be in an invalid state.
    """
