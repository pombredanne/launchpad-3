-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE ArchiveFile (
    id serial PRIMARY KEY,
    archive integer NOT NULL REFERENCES archive ON DELETE CASCADE,
    container text NOT NULL,
    path text NOT NULL,
    library_file integer NOT NULL REFERENCES libraryfilealias,
    scheduled_deletion_date timestamp without time zone
);

COMMENT ON TABLE ArchiveFile IS 'A file in an archive.';
COMMENT ON COLUMN ArchiveFile.archive IS 'The archive containing the file.';
COMMENT ON COLUMN ArchiveFile.container IS 'An identifier for the component that manages this file.';
COMMENT ON COLUMN ArchiveFile.path IS 'The path to the file within the published archive.';
COMMENT ON COLUMN ArchiveFile.library_file IS 'The file in the librarian.';
COMMENT ON COLUMN ArchiveFile.scheduled_deletion_date IS 'The date when this file should stop being published.';

CREATE INDEX archivefile__archive__container__idx
    ON ArchiveFile (archive, container);
CREATE INDEX archivefile__archive__scheduled_deletion_date__container__idx
    ON ArchiveFile (archive, scheduled_deletion_date, container)
    WHERE scheduled_deletion_date IS NOT NULL;
CREATE INDEX archivefile__archive__path__idx
    ON ArchiveFile (archive, path);
CREATE INDEX archivefile__library_file__idx
    ON ArchiveFile (library_file);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 74, 0);
