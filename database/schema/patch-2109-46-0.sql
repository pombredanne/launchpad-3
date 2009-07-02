SET client_min_messages=ERROR;

-- Add a column to configure whether the authorisation page should be
-- skipped by default for a given OpenID relying party.

ALTER TABLE openidrpconfig
  ADD COLUMN auto_authorize boolean NOT NULL DEFAULT FALSE;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 46, 0);

