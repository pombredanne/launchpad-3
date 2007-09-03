SET client_min_messages=ERROR;

CREATE TABLE LanguagePack (
    id serial NOT NULL PRIMARY KEY,
    file integer NOT NULL REFERENCES libraryfilealias(id),
    date_exported timestamp without time zone NOT NULL
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    date_last_use timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    distro_release integer NOT NULL REFERENCES DistroRelease(id),
    type integer NOT NULL DEFAULT 0,
    language_pack_that_updates integer REFERENCES LanguagePack(id)
);

ALTER TABLE LanguagePack
    ADD CONSTRAINT language_pack_type_update_has_reference_when_needed
    CHECK ((type = 1 AND language_pack_that_updates IS NOT NULL) OR
           (type = 0 AND language_pack_that_updates IS NULL));

COMMENT ON TABLE LanguagePack IS 'Store exported language packs for
DistroReleases.';
COMMENT ON COLUMN LanguagePack.file IS 'Librarian file where the language pack
is stored.';
COMMENT ON COLUMN LanguagePack.date_exported IS 'When was exported the
language pack.';
COMMENT ON COLUMN LanguagePack.date_last_use IS 'When did we stop using the
language pack. It\'s used to decide whether we can remove it completely from
the system. When it\'s being used, its value is NULL';
COMMENT ON COLUMN LanguagePack.distro_release IS 'The distribution release
from where this language pack was exported.';
COMMENT ON COLUMN LanguagePack.type IS 'Type of language pack. There are two
types available, 0: Full export, 1: Update export based on
language_pack_that_updates export.';
COMMENT ON COLUMN LanguagePack.language_pack_that_updates IS 'The LanguagePack
that this one updates.';

ALTER TABLE DistroRelease
    ADD COLUMN language_pack_base integer REFERENCES LanguagePack(id);
ALTER TABLE DistroRelease
    ADD COLUMN language_pack_delta integer REFERENCES LanguagePack(id);
ALTER TABLE DistroRelease
    ADD COLUMN language_pack_proposed integer REFERENCES LanguagePack(id);
ALTER TABLE DistroRelease
    ADD COLUMN language_pack_full_export_requested BOOLEAN DEFAULT FALSE;
ALTER TABLE DistroRelease
    ALTER COLUMN language_pack_full_export_requested SET NOT NULL;
ALTER TABLE DistroRelease
    ADD CONSTRAINT distrorelease_has_language_pack_base
    CHECK (language_pack_base IS NOT NULL OR language_pack_delta IS NULL);

COMMENT ON COLUMN DistroRelease.language_pack_base IS 'Current full export
language pack for this distribution release.';
COMMENT ON COLUMN DistroRelease.language_pack_delta IS 'Current language pack
update based on language_pack_base information.';
COMMENT ON COLUMN DistroRelease.language_pack_proposed IS 'Either a full or
update language pack being tested to be used in language_pack_base or
language_pack_delta.';
COMMENT ON COLUMN DistroRelease.language_pack_full_export_requested IS
'Whether next language pack export should be a full export or an update.';

ALTER TABLE Distribution
    ADD COLUMN language_pack_admin integer REFERENCES Person(id);
COMMENT ON COLUMN Distribution.language_pack_admin IS 'The Person or Team
that handle language packs for the distro release.';

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 99, 0);
