# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""VCS-agnostic view aliases that show the default VCS."""

__metaclass__ = type

from zope.component import getMultiAdapter

from lp.registry.enums import VCSType
from lp.services.webapp import stepto


class TargetDefaultVCSNavigationMixin:

    @stepto("+code")
    def traverse_code_view(self):
        if self.context.pillar.vcs in (VCSType.BZR, None):
            view_name = '+branches'
        elif self.context.pillar.vcs == VCSType.GIT:
            view_name = '+git'
        else:
            raise AssertionError("Unknown VCS")
        return getMultiAdapter(
            (self.context, self.request), name=view_name)


class PersonTargetDefaultVCSNavigationMixin:

    @stepto("+code")
    def traverse_code_view(self):
        if self.context.product.vcs in (VCSType.BZR, None):
            view_name = '+branches'
        elif self.context.product.vcs == VCSType.GIT:
            view_name = '+git'
        else:
            raise AssertionError("Unknown VCS")
        return getMultiAdapter(
            (self.context, self.request), name=view_name)
