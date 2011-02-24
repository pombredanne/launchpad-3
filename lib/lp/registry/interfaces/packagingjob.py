# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.interface import (
    Attribute,
    )

from canonical.launchpad import _
from lp.services.job.interfaces.job import IJob


class IPackagingJob(IJob):

    productseries = Attribute(_("The productseries of the Packaging."))

    productseries = Attribute(_("The productseries of the Packaging."))

    distroseries = Attribute(_("The distroseries of the Packaging."))

    sourcepackagename = Attribute(_("The sourcepackagename of the Packaging."))
