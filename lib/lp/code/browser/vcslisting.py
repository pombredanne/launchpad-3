# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""VCS-agnostic view aliases that show the default VCS."""

__metaclass__ = type

from zope.component import queryMultiAdapter

from lp.registry.enums import VCSType
from lp.registry.interfaces.persondistributionsourcepackage import (
    IPersonDistributionSourcePackage,
    )
from lp.registry.interfaces.personproduct import IPersonProduct
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
        return queryMultiAdapter(
            (self.context, self.request), name=view_name)


class PersonTargetDefaultVCSNavigationMixin:

    @stepto("+code")
    def traverse_code_view(self):
        if IPersonProduct.providedBy(self.context):
            target = self.context.product
        elif IPersonDistributionSourcePackage.providedBy(self.context):
            target = self.context.distro_source_package
        else:
            raise AssertionError("Unknown target: %r" % self.context)
        if target.pillar.vcs in (VCSType.BZR, None):
            view_name = '+branches'
        elif target.pillar.vcs == VCSType.GIT:
            view_name = '+git'
        else:
            raise AssertionError("Unknown VCS")
        return queryMultiAdapter(
            (self.context, self.request), name=view_name)
