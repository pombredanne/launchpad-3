-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE OAuthNonce
    ADD CONSTRAINT oauthnonce__access_token__fk
        FOREIGN KEY (access_token) REFERENCES OAuthAccessToken;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 42, 0);

