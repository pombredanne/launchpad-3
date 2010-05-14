-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);

/*
Existing Schema:

CREATE TABLE distributionsourcepackage (
    id integer NOT NULL,
    distribution integer NOT NULL,
    sourcepackagename integer NOT NULL,
    bug_reporting_guidelines text,
    max_bug_heat integer
);
*/

ALTER TABLE DistributionSourcePackage ADD COLUMN bug_count INTEGER;
ALTER TABLE DistributionSourcePackage ADD COLUMN po_message_count INTEGER;
ALTER TABLE DistributionSourcePackage
    ADD COLUMN section INTEGER NOT NULL REFERENCES section(id);

CREATE FUNCTION distributionsourcepackage_maintain() RETURNS trigger
    AS $$
    DECLARE
        distro integer;
        spn integer;
    BEGIN
        SELECT distribution INTO distro
        FROM DistroSeries
        WHERE id = NEW.distroseries;

        SELECT sourcepackagename INTO spn
        FROM SourcePackageRelease
        WHERE id = NEW.sourcepackagerelease;

        BEGIN
            INSERT INTO DistributionSourcePackage (
                distribution,
                sourcepackagename,
                section
            ) VALUES (
                distro,
                spn,
                NEW.section
            );
        EXCEPTION WHEN unique_violation THEN
            -- If an entry already exists for a given
            -- distribution+sourcepackagename, then just update
            -- the section.
            UPDATE DistributionSourcePackage
            SET section = NEW.section
            WHERE distribution = distro
                AND sourcepackagename = spn;
        END;
        RETURN NULL; -- Ignored - this is an AFTER trigger
    END;
    $$
LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION distributionsourcepackage_maintain() IS
'Trigger maintaining the DistributionSourcePackage table based on inserts to the SourcePackagePublishingHistory table.';

CREATE TRIGGER distributionsourcepackage_maintain_trigger
    AFTER INSERT ON SourcePackagePublishingHistory
    FOR EACH ROW
    EXECUTE PROCEDURE distributionsourcepackage_maintain();


/* TEST

\x
SELECT * INTO TEMP spph
FROM SourcePackagePublishingHistory
WHERE id = 1;

DELETE FROM SourcePackagePublishingHistory
WHERE id = 1;

\echo DSP before insert (zero rows)
SELECT * FROM DistributionSourcePackage;

INSERT INTO SourcePackagePublishingHistory
SELECT * FROM spph;

\echo DSP after insert (one row)
SELECT * FROM DistributionSourcePackage;

UPDATE spph SET id = 999, section = 35 WHERE id = 1;
INSERT INTO SourcePackagePublishingHistory
SELECT * FROM spph;

\echo DSP after 2nd insert (still one row, but with a different section)
SELECT * FROM DistributionSourcePackage;

END TEST */
