SET client_min_messages=ERROR;

ALTER TABLE StructuralSubscription
  DROP CONSTRAINT one_target;

ALTER TABLE StructuralSubscription
  ADD CONSTRAINT one_target CHECK (
    null_count(ARRAY[product, productseries, project,
                     distroseries, distribution, milestone]) = 5);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 03, 0);
