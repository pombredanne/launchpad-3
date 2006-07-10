SET client_min_messages=ERROR;

-- This constraint causes database restores to take way to long,
-- as the standard tools create the tables with their CHECK constraints
-- and then load the data *before* creating indexes. This might be a
-- PostgreSQL issue. Dropping the constraint is easiest for now as we
-- don't really need it.
ALTER TABLE ShippingRequest DROP CONSTRAINT is_person;
ALTER TABLE Vote DROP CONSTRAINT is_person;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 14, 1);

