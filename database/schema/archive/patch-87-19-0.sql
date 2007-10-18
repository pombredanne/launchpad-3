SET client_min_messages=ERROR;

ALTER TABLE Product ADD COLUMN private_bugs boolean NOT NULL DEFAULT FALSE;
ALTER TABLE Product ADD COLUMN private_specs boolean NOT NULL DEFAULT FALSE;

ALTER TABLE Product ADD CONSTRAINT private_bugs_need_contact CHECK (
    private_bugs IS FALSE OR bugcontact IS NOT NULL
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 19, 0);

