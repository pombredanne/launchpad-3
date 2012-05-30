# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Classes for scripts to work with ProductJobs."""

__metaclass__ = type
__all__ = [
    'ProductJobManager',
    ]


class ProductJobManager:

    def __init__(self, logger):
        self.logger = logger
