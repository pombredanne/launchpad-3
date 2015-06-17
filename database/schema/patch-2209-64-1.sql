-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Fill in build_by_default processors for all archives.
INSERT INTO archivearch (archive, processor)
    SELECT archive.id, processor.id
        FROM archive, processor
        WHERE
            archive.purpose != 6 -- Copy archives handle ArchiveArch specially.
            AND processor.name IN ('i386', 'amd64', 'lpia', '386')
    EXCEPT
    SELECT archive, processor FROM archivearch;

-- And fill in unrestricted non-virt-only arches for non-virt archives.
INSERT INTO archivearch (archive, processor)
    SELECT archive.id, processor.id
        FROM archive, processor
        WHERE
            archive.purpose != 6 -- Copy archives handle ArchiveArch specially.
            AND NOT archive.require_virtualized
            AND processor.name IN ('sparc', 'ia64', 'hppa')
    EXCEPT
    SELECT archive, processor FROM archivearch;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 64, 1);
