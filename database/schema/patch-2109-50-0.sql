SET client_min_messages=ERROR;

ALTER TABLE Branch
    ADD COLUMN owner_name text,
    ADD COLUMN target_suffix text,
    ADD COLUMN unique_name text;

UPDATE Branch SET
    owner_name = person_name,
    target_suffix = COALESCE(product_name, spn_name),
    unique_name = '~' || person_name || '/' || COALESCE(
        product_name,
        distribution_name || '/' || distroseries_name || '/' || spn_name,
        '+junk') || '/' || Branch.name
FROM (
    SELECT
        Branch.id AS branch,
        Person.name AS person_name,
        Product.name AS product_name,
        Distribution.name AS distribution_name,
        Distroseries.name AS distroseries_name,
        SPN.name AS spn_name
    FROM Branch
    JOIN Person ON Person.id = Branch.owner
    LEFT OUTER JOIN DistroSeries ON Branch.distroseries = DistroSeries.id
    LEFT OUTER JOIN Product ON Branch.product = Product.id
    LEFT OUTER JOIN Distribution ON Distroseries.distribution = Distribution.id
    LEFT OUTER JOIN SourcepackageName AS SPN
        ON SPN.id = Branch.sourcepackagename
    ) AS BranchInfo
WHERE Branch.id = BranchInfo.branch;

ALTER TABLE Branch
    ALTER COLUMN owner_name SET NOT NULL,
    ADD CONSTRAINT branch__unique_name__key UNIQUE (unique_name);

CREATE INDEX branch__owner_name__idx ON Branch(owner_name);
CREATE INDEX branch__target_suffix__idx ON Branch(target_suffix);


-- Maintain name cache on Branch changes.
CREATE TRIGGER update_branch_name_cache_t BEFORE INSERT OR UPDATE ON Branch
FOR EACH ROW EXECUTE PROCEDURE update_branch_name_cache();

-- Maintain Branch name cache on Person update.
CREATE TRIGGER mv_branch_person_update_t AFTER UPDATE ON Person
FOR EACH ROW EXECUTE PROCEDURE mv_branch_person_update();

-- Maintain Branch name cache on Product update.
CREATE TRIGGER mv_branch_product_update_t AFTER UPDATE ON Product
FOR EACH ROW EXECUTE PROCEDURE mv_branch_product_update();

-- Maintain Branch name cache on Distroseries update.
CREATE TRIGGER mv_branch_distroseries_update_t AFTER UPDATE ON Distroseries
FOR EACH ROW EXECUTE PROCEDURE mv_branch_distroseries_update();

-- Maintain Branch name cache on Distribution update.
CREATE TRIGGER mv_branch_distribution_update_t AFTER UPDATE ON Distribution
FOR EACH ROW EXECUTE PROCEDURE mv_branch_distribution_update();

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 50, 0);
