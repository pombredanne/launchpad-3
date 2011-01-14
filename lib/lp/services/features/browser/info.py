# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View and edit feature rules."""

__metaclass__ = type
__all__ = [
    'FeatureInfoView',
    ]


from collections import namedtuple
from textwrap import dedent

from canonical.launchpad.webapp.publisher import LaunchpadView
from lp.services.features.flags import (
    flag_info,
    undocumented_flags,
    )
from lp.services.features.scopes import HANDLERS


# Named tuples to use when passing flag and scope data to the template.
Flag = namedtuple('Flag', ('name', 'domain', 'description', 'default'))
Scope = namedtuple('Scope', ('regex', 'description'))


def docstring_dedent(s):
    """Remove leading indentation from a doc string.

    Since the first line doesn't have indentation, split it off, dedent, and
    then reassemble.
    """
    # Make sure there is at least one newline so the split works.
    first, rest = (s+'\n').split('\n', 1)
    return (first + '\n' + dedent(rest)).strip()


class FeatureInfoView(LaunchpadView):
    """Display feature flag documentation and other info."""

    page_title = label = 'Feature flag info'

    @property
    def flag_info(self):
        """A list of flags as named tuples, ready to be rendered."""
        return map(Flag._make, flag_info)

    @property
    def undocumented_flags(self):
        """Flag names referenced during process lifetime but not documented.
        """
        return ', '.join(undocumented_flags)

    @property
    def scope_info(self):
        """A list of scopes as named tuples, ready to be rendered."""
        return [
            Scope._make((handler.pattern, docstring_dedent(handler.__doc__)))
            for handler in HANDLERS]
