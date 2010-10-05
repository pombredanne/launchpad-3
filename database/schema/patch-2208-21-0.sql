SET client_min_messages=ERROR;

CREATE TABLE lp_OpenIdidentifier (
    identifier text PRIMARY KEY,
    account    integer NOT NULL REFERENCES lp_person(account),
    date_created timestamp without time zone NOT NULL);

INSERT INTO lp_OpenIdIdentifier (identifier, account, date_created)
SELECT identifier, account, date_created FROM OpenIdIdentifier
WHERE identifier NOT IN (SELECT identifier FROM lp_OpenIdIdentifier);


INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 21, 0);
