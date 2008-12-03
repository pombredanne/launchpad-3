--
-- Data fix
--

BEGIN;

SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

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
 WHERE bugnomination.id = bugnomination_broken.id
RETURNING bugnomination.*;

-- End
