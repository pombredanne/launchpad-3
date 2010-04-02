# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper functions dealing with registration in tests.
"""
__metaclass__ = type

__all__ = [
    'get_captcha_answer',
    'set_captcha_answer',
    ]

import re


def get_captcha_answer(contents):
    """Search the browser contents and get the captcha answer."""
    expr = re.compile("(\d+ .{1} \d+) =")
    match = expr.search(contents)
    if match:
        question = match.group(1)
        answer = eval(question)
        return str(answer)
    return ''


def set_captcha_answer(browser, answer=None, prefix=''):
    """Given a browser, set the login captcha with the correct answer."""
    if answer is None:
        answer = get_captcha_answer(browser.contents)
    browser.getControl(name=prefix + 'captcha_submission').value = (
        answer)
