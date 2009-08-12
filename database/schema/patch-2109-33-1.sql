-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Backport of index to fix Bug #337922

CREATE INDEX oauthnonce__access_token__request_timestamp__idx
    ON OAuthNonce(access_token, request_timestamp);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 33, 1);

