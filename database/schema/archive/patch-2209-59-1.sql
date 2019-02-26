-- Copyright 2014 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Populate BinaryPackageBuild.arch_indep based on nominatedarchindep.
-- On production this is done by a garbo job.
UPDATE binarypackagebuild
SET arch_indep = (distroarchseries.id = distroseries.nominatedarchindep)
FROM distroarchseries, distroseries
WHERE
    distroarchseries.id = binarypackagebuild.distro_arch_series
    AND distroseries.id = distroarchseries.distroseries;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 59, 1);
