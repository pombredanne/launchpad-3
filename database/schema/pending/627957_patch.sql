SET client_min_messages=ERROR;

-- Allow for package diffs against both derived and parent versions.
ALTER TABLE DistroSeriesDifference ADD COLUMN parent_package_diff integer CONSTRAINT distroseriesdifference__parent_package_diff__fk REFERENCES packagediff;
CREATE INDEX distroseriesdifference__parent_package_diff__idx ON distroseriesdifference(parent_package_diff);

-- Add columns for source_pub and parent_source_pub
ALTER TABLE DistroSeriesDifference ADD COLUMN source_pub integer CONSTRAINT distroseriesdifference__source_pub__fk REFERENCES sourcepackagepublishinghistory;
CREATE INDEX distroseriesdifference__source_pub__idx ON distroseriesdifference(source_pub);
ALTER TABLE DistroSeriesDifference ADD COLUMN parent_source_pub integer CONSTRAINT distroseriesdifference__parent_source_pub__fk REFERENCES sourcepackagepublishinghistory;
CREATE INDEX distroseriesdifference__parent_source_pub__idx ON distroseriesdifference(parent_source_pub);

-- The derived_series column is now redundant as source_pub.distroseries
-- defines it.
ALTER TABLE DistroSeriesDifference DROP COLUMN derived_series;

-- We no longer necessarily need the source_package_name column since it will
-- be referenced by
-- (parent_)source_pub.sourcepackagerelease.sourcepackagename, but we do want
-- to ensure that both the source_pub and parent_source_pub reference the same
-- source package name.
ALTER TABLE DistroSeriesDifference DROP COLUMN source_package_name;
-- DROP INDEX distroseriesdifference__source_package_name__idx;

-- Ensure that source_pub and parent_source_pub always refer to the same
-- source package name, and that it is unique for the derived series.
CREATE OR REPLACE FUNCTION "distroseriesdifference_ensure_consistent_package_names"()
RETURNS trigger LANGUAGE 'plpgsql' AS
$$
DECLARE
    source_package_name_id integer;
    parent_source_package_name_id integer;
BEGIN
    -- Ensure parent_source_pub is for parent series.

    -- Only do this if both are defined.
    SELECT INTO source_package_name_id sourcepackagerelease.sourcepackagename
    FROM sourcepackagerelease, sourcepackagepublishinghistory
    WHERE
        sourcepackagerelease.id = sourcepackagepublishinghistory.sourcepackagerelease AND
        sourcepackagepublishinghistory.id = NEW.source_pub;

    SELECT INTO parent_source_package_name_id sourcepackagerelease.sourcepackagename
    FROM sourcepackagerelease, sourcepackagepublishinghistory
    WHERE
        sourcepackagerelease.id = sourcepackagepublishinghistory.sourcepackagerelease AND
        sourcepackagepublishinghistory.id = NEW.parent_source_pub;

    IF source_package_name_id <> parent_source_package_name_id THEN
        RAISE EXCEPTION 'source_pub and parent_source_pub have different source package names.';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER distroseriesdifference__source_package_name__consistent
    BEFORE INSERT OR UPDATE ON DistroSeriesDifference
    FOR EACH ROW EXECUTE PROCEDURE distroseriesdifference_ensure_consistent_package_names();
