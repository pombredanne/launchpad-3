SET client_min_messages=ERROR;

ALTER TABLE OpenIdRpConfig
    ADD COLUMN query_all_teams BOOLEAN NOT NULL DEFAULT FALSE;
  
UPDATE OpenIdRpConfig SET query_all_teams=TRUE
WHERE (
        trust_root LIKE 'https://%.canonical.com'
        OR trust_root = 'https://www.ubuntuone.com/'
        OR trust_root LIKE 'https://%.launchpad.net'
    )
    AND trust_root NOT LIKE  '%shop%';


INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 8, 0);
