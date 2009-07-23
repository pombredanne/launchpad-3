-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE OpenIdAuthorization
    DROP CONSTRAINT openidauthorization_person_fkey;

DROP INDEX openidauthorization__person__client_id__trust_root__unq;
DROP INDEX openidauthorization__person__trust_root__unq;
DROP INDEX openidauthorization__person__trust_root__date_expires__client_i;

UPDATE OpenIdAuthorization SET person=account
FROM Person
WHERE OpenIdAuthorization.person = Person.id;

ALTER TABLE OpenIdAuthorization RENAME person TO account;

CREATE UNIQUE INDEX openidauthorization__account__client_id__trust_root__key
    ON OpenIdAuthorization (account, client_id, trust_root)
    WHERE client_id IS NOT NULL;
CREATE UNIQUE INDEX openidauthorixation__account__trust_root__key
    ON OpenIdAuthorization (account, trust_root)
    WHERE client_id IS NULL;
CREATE INDEX openidauthorixation__account__troot__expires__client_id__idx
    ON OpenIdAuthorization (account, trust_root, date_expires, client_id);

ALTER TABLE OpenIdAuthorization
    ADD CONSTRAINT openidauthorization__account__fk
    FOREIGN KEY (account) REFERENCES Account;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 17, 0);
