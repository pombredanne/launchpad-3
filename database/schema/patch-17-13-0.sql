SET client_min_messages=ERROR;

-- Ensure only one preferred email address. Also doubles as an index on person,
-- so drop the existing one too.
-- Can't seem to get this accepted as an actual constraint using ALTER TABLE
-- but the index will work just as well.
DROP INDEX emailaddress_person_idx;
CREATE UNIQUE INDEX emailaddress_person_key 
    ON EmailAddress(person, (NULLIF(status=4, false)));

--ALTER TABLE EmailAddress ADD CONSTRAINT emailaddress_person_key
--    UNIQUE (person, (NULLIF(status = 4, false)));

-- Add a check to ensure teams don't get passwords set, as requested by
-- Salgado I think.
ALTER TABLE Person ADD CONSTRAINT valid_team_fields CHECK (
    teamowner IS NULL OR (
        givenname IS NULL
        AND familyname IS NULL
        AND password IS NULL
        AND language IS NULL
        )
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 13, 0);
