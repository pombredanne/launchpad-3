#!/usr/bin/python2.4

# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

""" Expire all questions in the OPEN and NEEDSINFO states that didn't receive
any activity in the last X days.

The expiration period is configured through
config.answertracker.days_before_expiration
"""

__metaclass__ = type

__all__ = ['ExpireQuestions']


import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.scripts.questionexpiration import QuestionJanitor


class ExpireQuestions(LaunchpadCronScript):
    """Expire old questions.

    This script expires questions in the OPEN and NEEDSINFO states that
    didn't have any activity in the last X days. The number of days is
    configured through config.answertracker.days_before_expiration.
    """
    usage = "usage: %prog [options]"
    description =  __doc__


    def main(self):
        """Expire old questions."""
        janitor = QuestionJanitor(log=self.logger)
        janitor.expireQuestions(self.txn)


if __name__ == '__main__':
    script = ExpireQuestions('expire-questions',
        dbuser=config.answertracker.dbuser)
    script.lock_and_run()

