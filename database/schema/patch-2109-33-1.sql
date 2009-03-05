SET client_min_messages=ERROR;

-- Backport of index to fix Bug #337922

CREATE INDEX oauthnonce__access_token__request_timestamp__idx
    ON OAuthNonce(access_token, request_timestamp);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 33, 1);

