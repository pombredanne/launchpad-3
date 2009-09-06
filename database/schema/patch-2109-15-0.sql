-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

--
-- Data migration - fix bugnominations with bad or duplicate targets.
--

-- Collect all bugnominations which have multiple identical
-- bug+distroseries or bug+productseries.
CREATE TEMPORARY TABLE bugnomination_broken
ON COMMIT DROP
AS (SELECT nom.*
      FROM bugnomination AS nom,
           (SELECT bug, distroseries
              FROM bugnomination
             GROUP BY bug, distroseries
            HAVING COUNT(distroseries) > 1) AS broken
     WHERE nom.bug = broken.bug
       AND nom.distroseries = broken.distroseries
    UNION ALL
    SELECT nom.*
      FROM bugnomination AS nom,
           (SELECT bug, productseries
              FROM bugnomination
             GROUP BY bug, productseries
            HAVING COUNT(productseries) > 1) AS broken
     WHERE nom.bug = broken.bug
       AND nom.productseries = broken.productseries);

-- From the broken table, remove the one bugnomination we want to keep
-- for each bug+distroseries combination. Oldest and highest status
-- wins.
DELETE FROM bugnomination_broken
 WHERE id IN (
    SELECT DISTINCT ON (bug, distroseries) id
      FROM bugnomination_broken
     WHERE distroseries IS NOT NULL
     ORDER BY bug, distroseries, date_created ASC, status DESC);

-- From the broken table, remove the one bugnomination we want to keep
-- for each bug+productseries combination. Oldest and highest status
-- wins.
DELETE FROM bugnomination_broken
 WHERE id IN (
    SELECT DISTINCT ON (bug, productseries) id
      FROM bugnomination_broken
     WHERE productseries IS NOT NULL
     ORDER BY bug, productseries, date_created ASC, status DESC);

-- Delete the broken bugnominations.
DELETE FROM bugnomination
 USING bugnomination_broken
 WHERE bugnomination.id = bugnomination_broken.id;


--
-- Add bugnomination constraints to stop bad data.
--
CREATE UNIQUE INDEX bugnomination__distroseries__bug__key
    ON bugnomination (distroseries, bug) WHERE distroseries IS NOT NULL;

CREATE UNIQUE INDEX bugnomination__productseries__bug__key
    ON bugnomination (productseries, bug) WHERE productseries IS NOT NULL;

ALTER TABLE bugnomination ADD CONSTRAINT distroseries_or_productseries
    CHECK (distroseries IS NULL <> productseries IS NULL);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 15, 0);

