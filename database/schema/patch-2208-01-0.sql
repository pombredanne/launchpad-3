SET client_min_messages=ERROR;

CREATE TABLE OpenIdIdentifier (
    identifier text PRIMARY KEY,
    account integer NOT NULL REFERENCES Account,
    date_created timestamp without time zone NOT NULL
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);

CREATE INDEX openididentity__account__idx ON OpenIDIdentifier(account);


-- XXX: Should data be migrated? Existing data is just tokens, not the
-- full URL. If we can convert this old data to URLs, we should add a
-- CHECK constraint to OpenIDIdentifier.identifier too.
INSERT INTO OpenIdIdentifier (identifier, account, date_created)
SELECT openid_identifier, id, date_created FROM Account;

ALTER TABLE Account
    DROP COLUMN openid_identifier,
    DROP COLUMN old_openid_identifier;


INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 01, 0);
