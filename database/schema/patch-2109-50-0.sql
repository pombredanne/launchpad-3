SET client_min_messages=ERROR;

CREATE TABLE BranchPath (
    id serial PRIMARY KEY,
    branch integer NOT NULL
        CONSTRAINT branchpath__branch__key UNIQUE
        CONSTRAINT branchpath__branch__fk REFERENCES Branch
            ON DELETE CASCADE,
    owner_name text NOT NULL,
    target_suffix text,
    path text NOT NULL
        CONSTRAINT branchpath__path__key UNIQUE
);

INSERT INTO BranchPath (branch, owner_name, target_suffix, path)
SELECT
    Branch.id,
    Owner.name,
    COALESCE(Product.name, SPN.name),
    '~' || Owner.name || '/' || COALESCE(
        Product.name,
        Distribution.name || '/' || Distroseries.name || '/' || SPN.name,
        '+junk') || '/' || branch.name
FROM Branch
LEFT OUTER JOIN DistroSeries ON Branch.distroseries = DistroSeries.id
LEFT OUTER JOIN Product ON Branch.product = Product.id
LEFT OUTER JOIN Distribution ON Distroseries.distribution = Distribution.id
LEFT OUTER JOIN SourcepackageName AS SPN
    ON SPN.id = Branch.sourcepackagename
JOIN Person AS Owner ON Owner.id = Branch.owner
ORDER BY Branch.id; -- order by required to make patch deterministic
                    -- and replication friendly.

CREATE INDEX branchpath__owner_name__idx ON BranchPath(owner_name);
CREATE INDEX branchpath__target_suffix__idx ON BranchPath(target_suffix);

-- Insert new records into the cache on Branch creation.
CREATE TRIGGER mv_branchpath_branch_insert_t AFTER INSERT ON Branch
FOR EACH ROW EXECUTE PROCEDURE mv_branchpath_branch_insert();

-- Maintain BranchPath records on Branch update.
CREATE TRIGGER mv_branchpath_branch_update_t AFTER UPDATE ON Branch
FOR EACH ROW EXECUTE PROCEDURE mv_branchpath_branch_update();

-- Maintain BranchPath records on Person update.
CREATE TRIGGER mv_branchpath_person_update_t AFTER UPDATE ON Person
FOR EACH ROW EXECUTE PROCEDURE mv_branchpath_person_update();

-- Maintain BranchPath records on Product update.
CREATE TRIGGER mv_branchpath_product_update_t AFTER UPDATE ON Product
FOR EACH ROW EXECUTE PROCEDURE mv_branchpath_product_update();

-- Maintain BranchPath records on Distroseries update.
CREATE TRIGGER mv_branchpath_distroseries_update_t AFTER UPDATE ON Distroseries
FOR EACH ROW EXECUTE PROCEDURE mv_branchpath_distroseries_update();

-- Maintain BranchPath records on Distribution update.
CREATE TRIGGER mv_branchpath_distribution_update_t AFTER UPDATE ON Distribution
FOR EACH ROW EXECUTE PROCEDURE mv_branchpath_distribution_update();

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 50, 0);
