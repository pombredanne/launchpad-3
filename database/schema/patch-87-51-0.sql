SET client_min_messages=ERROR;

CREATE TABLE LanguagePack (
    id serial NOT NULL PRIMARY KEY,
    file integer NOT NULL
        CONSTRAINT languagepack__file__fk REFERENCES LibraryFileAlias,
    date_exported timestamp without time zone NOT NULL
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    date_last_used timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    distroseries integer NOT NULL
        CONSTRAINT languagepackage__distroseries__fk
        REFERENCES DistroRelease(id),
    type integer NOT NULL DEFAULT 1,
    updates integer
        CONSTRAINT languagepack__updates__fk
        REFERENCES LanguagePack(id),
    CONSTRAINT valid_updates CHECK (
        (type = 2 AND updates IS NOT NULL) OR
        (type = 1 AND updates IS NULL)
        )
);

CREATE INDEX languagepack__file__idx ON LanguagePack(file);

ALTER TABLE DistroRelease ADD COLUMN language_pack_base integer
    CONSTRAINT distroseries__language_pack_base__fk
    REFERENCES LanguagePack(id);
ALTER TABLE DistroRelease ADD COLUMN language_pack_delta integer
    CONSTRAINT distroseries__language_pack_delta__fk
    REFERENCES LanguagePack(id);
ALTER TABLE DistroRelease ADD COLUMN language_pack_proposed integer
    CONSTRAINT distroseries__language_pack_proposed__fk
    REFERENCES LanguagePack(id);
ALTER TABLE DistroRelease
    ADD COLUMN language_pack_full_export_requested BOOLEAN DEFAULT FALSE
    NOT NULL;
ALTER TABLE DistroRelease
    ADD CONSTRAINT valid_language_pack_delta
    CHECK (language_pack_base IS NOT NULL OR language_pack_delta IS NULL);


ALTER TABLE Distribution
    ADD COLUMN language_pack_admin integer REFERENCES Person(id);
CREATE INDEX distribution__language_pack_admin__idx
    ON Distribution(language_pack_admin);


INSERT INTO LaunchpadDatabaseRevision VALUES (87, 51, 0);
