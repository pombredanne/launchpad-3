SET client_min_messages=ERROR;

/* Product.name is now UNIQUE. Products do not need a project. */
ALTER TABLE Product ALTER COLUMN project DROP NOT NULL;
ALTER TABLE Product ADD CONSTRAINT product_name_key UNIQUE(name);
ALTER TABLE Product DROP CONSTRAINT product_project_key;
ALTER TABLE Product DROP CONSTRAINT product_id_key;
CREATE INDEX product_project_idx ON Product(project);
ALTER TABLE Product DROP CONSTRAINT "$2";
ALTER TABLE Product ADD CONSTRAINT product_owner_fk
    FOREIGN KEY("owner") REFERENCES Person(id);
ALTER TABLE Product DROP CONSTRAINT "$1";
ALTER TABLE Product ADD CONSTRAINT product_project_fk
    FOREIGN KEY(project) REFERENCES Project(id);

UPDATE LaunchpadDatabaseRevision SET major=6,minor=3,patch=0;

