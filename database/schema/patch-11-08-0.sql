SET client_min_messages=ERROR;


CREATE TABLE POTemplateName (
  id        serial PRIMARY KEY,
  name      text NOT NULL,
  title     text NOT NULL,
  description text,
  CONSTRAINT potemplate_name_key UNIQUE(name),
  CONSTRAINT potemplate_valid_name CHECK(valid_name(name))
);

ALTER TABLE POTemplate ADD COLUMN potemplatename integer
    CONSTRAINT potemplate_potemplatename_fk REFERENCES POTemplateName(id);
ALTER TABLE POTemplate ADD COLUMN productrelease integer 
    CONSTRAINT potemplate_productrelease_fk REFERENCES ProductRelease(id);

ALTER TABLE POTemplate ADD CONSTRAINT potemplate_productrelease_key 
    UNIQUE(productrelease, potemplatename);
ALTER TABLE POTemplate ADD CONSTRAINT potemplate_distrorelease_key
    UNIQUE(distrorelease, sourcepackagename, potemplatename);

ALTER TABLE POTemplate DROP CONSTRAINT potemplate_rawimportstatus_valid;

/* Migration */

-- Set the owner to rosetta-admins
UPDATE POTemplate SET owner=Person.id
    FROM Person
    WHERE Person.name='rosetta-admins' AND POTemplate.owner IS NULL;

-- Add entries to POTemplateName, and update the POTemplates to reference them
INSERT INTO POTemplateName (name, title)  (
    SELECT name, title FROM POTemplate
    );
UPDATE POTemplate SET potemplatename=POTemplateName.id
    FROM POTemplateName WHERE POTemplateName.name=POTemplate.name;

-- Add dummy ProductRelease
INSERT INTO ProductRelease (product, datereleased, version, owner) (
    SELECT
        Product.id,
        CURRENT_TIMESTAMP AT TIME ZONE 'UTC',
        'unknown',
        Product.owner
    FROM
        Product JOIN POTemplate ON Product.id = POTemplate.product
    WHERE
        POTemplate.sourcepackagename IS NULL
    );

-- XXX: Work in progress. Ensure dummy productreleases are there
-- and link potemplates to them.


ALTER TABLE POTemplate ALTER COLUMN owner SET NOT NULL;
ALTER TABLE POTemplate ALTER COLUMN potemplatename SET NOT NULL;
ALTER TABLE POTemplate ALTER COLUMN rawfile SET NOT NULL;
ALTER TABLE POTemplate ALTER COLUMN rawimporter SET NOT NULL;
ALTER TABLE POTemplate ALTER COLUMN daterawimport SET NOT NULL;

ALTER TABLE POTemplate ADD CONSTRAINT valid_link CHECK (
    productrelease IS NULL <> distrorelease IS NULL
    AND distrorelease IS NULL = sourcepackagename IS NULL
    );

ALTER TABLE POTemplate DROP COLUMN product;
ALTER TABLE POTemplate DROP COLUMN branch;
ALTER TABLE POTemplate DROP COLUMN changeset;
ALTER TABLE POTemplate DROP COLUMN sourcepackagerelease;
ALTER TABLE POTemplate DROP COLUMN name;

INSERT INTO LaunchpadDatabaseRevision VALUES (11, 8, 0);

