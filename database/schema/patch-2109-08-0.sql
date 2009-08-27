-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE OpenIdRpConfig
    ADD COLUMN can_query_any_team BOOLEAN NOT NULL DEFAULT FALSE;
  
UPDATE OpenIdRpConfig SET can_query_any_team = TRUE
WHERE (
        trust_root LIKE 'https://%.canonical.com%'
        OR trust_root = 'https://www.ubuntuone.com/'
        OR trust_root LIKE 'https://%.launchpad.net%'
    )
    AND trust_root NOT LIKE  '%shop%';

ALTER TABLE ProductRelease
    ADD COLUMN milestone integer REFERENCES Milestone UNIQUE;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 8, 0);
