--
-- Constraints
--

CREATE UNIQUE INDEX bugnomination__unique_distroseries__idx
    ON bugnomination (bug, distroseries)
 WHERE distroseries IS NOT NULL;

CREATE UNIQUE INDEX bugnomination__unique_productseries__idx
    ON bugnomination (bug, productseries)
 WHERE productseries IS NOT NULL;

ALTER TABLE bugnomination
  ADD CONSTRAINT bugnomination__distroseries_or_productseries__constraint
CHECK ((distroseries IS NOT NULL AND productseries IS NULL) OR
       (distroseries IS NULL AND productseries IS NOT NULL));

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);

-- End
