# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = ['BuildPackageJob']


from storm.locals import Int, Reference, Storm

from zope.interface import implements

from lp.soyuz.interfaces.buildpackagejob import IBuildPackageJob


class BuildPackageJob(Storm):
    """See `IBuildPackageJob`."""
    implements(IBuildPackageJob)
    __storm_table__ = 'buildpackagejob'
    id = Int(primary=True)

    job_id = Int(name='job', allow_none=False)
    job = Reference(job_id, 'Job.id')

    build_id = Int(name='build', allow_none=False)
    build = Reference(build_id, 'Build.id')
