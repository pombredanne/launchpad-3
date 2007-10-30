SET client_min_messages=ERROR;

ALTER TABLE Product
    ADD COLUMN official_blueprints bool NOT NULL DEFAULT FALSE,
    ADD COLUMN enable_bug_expiration bool NOT NULL DEFAULT FALSE,
    ADD CONSTRAINT only_launchpad_has_expiration
        CHECK(enable_bug_expiration = FALSE OR official_malone = TRUE);

ALTER TABLE Distribution
    ADD COLUMN official_blueprints bool NOT NULL DEFAULT FALSE,
    ADD COLUMN enable_bug_expiration bool NOT NULL DEFAULT FALSE,
    ADD CONSTRAINT only_launchpad_has_expiration
        CHECK(enable_bug_expiration = FALSE OR official_malone = TRUE);

UPDATE Product
SET
    enable_bug_expiration = TRUE
WHERE
    official_malone = TRUE;

UPDATE Distribution
SET
    enable_bug_expiration = TRUE
WHERE
    official_malone = TRUE;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 97, 0);
