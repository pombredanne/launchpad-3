# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helpers for command line tools."""

__metaclass__ = type
__all__ = ["LPOptionParser"]

from copy import copy
from datetime import datetime
from optparse import (
    Option,
    OptionParser,
    OptionValueError,
    )

from canonical.launchpad.scripts.logger import logger_options


def _check_datetime(option, opt, value):
    "Type checker for optparse datetime option type."
    # We support 5 valid ISO8601 formats.
    formats = [
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
        ]
    for format in formats:
        try:
            return datetime.strptime(value, format)
        except ValueError:
            pass
    raise OptionValueError(
        "option %s: invalid datetime value: %r" % (opt, value))


class LPOption(Option):
    """Extended optparse Option class.

    Adds a 'datetime' option type.
    """
    TYPES = Option.TYPES + ("datetime", datetime)
    TYPE_CHECKER = copy(Option.TYPE_CHECKER)
    TYPE_CHECKER["datetime"] = _check_datetime
    TYPE_CHECKER[datetime] = _check_datetime


class LPOptionParser(OptionParser):
    """Extended optparse OptionParser.

    Adds a 'datetime' option type.

    Automatically adds our standard --verbose, --quiet options that
    tie into our logging system.
    """
    def __init__(self, *args, **kw):
        kw.setdefault('option_class', LPOption)
        OptionParser.__init__(self, *args, **kw)
        logger_options(self)

