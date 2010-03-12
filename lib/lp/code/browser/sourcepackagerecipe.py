# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""SourcePackageRecipe views."""

__metaclass__ = type

__all__ = []

from canonical.launchpad.webapp import (
    LaunchpadView)

class SourcePackageRecipeView(LaunchpadView):
    """Default view of a SourcePackageRecipe."""

    silly = 'silly'

    @property
    def base_branch(self):
        return self.context._recipe_data.base_branch
