
CREATE TABLE POTemplateName (
  id        serial PRIMARY KEY,
  name      text NOT NULL,
  title     text NOT NULL,
  description text,
  CONSTRAINT potemplate_name_key UNIQUE(name),
  CONSTRAINT potemplate_valid_name CHECK(valid_name(name))
);

ALTER TABLE POTemplate ADD COLUMN potemplatename integer REFERENCES POTemplateName(id);
ALTER TABLE POTemplate ADD COLUMN productrelease integer REFERENCES ProductRelease(id);

ALTER TABLE POTemplate ADD CONSTRAINT potemplate_productrelease_potemplatename_key UNIQUE(productrelease, potemplatename);
ALTER TABLE POTemplate ADD CONSTRAINT potemplate_distrorelease_sourcepackagename_potemplatename_key UNIQUE(distrorelease, sourcepackagename, potemplatename);

/*
 * Next SQL sentences need data migration before being executed.
 */

/*
ALTER TABLE POTemplate ALTER COLUMN owner SET NOT NULL;
ALTER TABLE POTemplate ALTER COLUMN rawfile SET NOT NULL;
ALTER TABLE POTemplate ALTER COLUMN rawimporter SET NOT NULL;
ALTER TABLE POTemplate ALTER COLUMN daterawimport SET NOT NULL;
*/

/*
ALTER TABLE POTemplate DROP COLUMN product;
ALTER TABLE POTemplate DROP COLUMN branch;
ALTER TABLE POTemplate DROP COLUMN changeset;
ALTER TABLE POTemplate DROP COLUMN sourcepackagerelease;
ALTER TABLE POTemplate DROP COLUMN name;
*/


COMMENT ON TABLE POTemplateName IS 'POTemplate Name. This table stores the domains/names of a set of POTemplate rows.';
COMMENT ON COLUMN POTemplateName.name IS 'The name of the POTemplate set. It must be unique';
COMMENT ON COLUMN POTemplateName.title IS 'The title we are going to use every time that we render a view of this POTemplateName row.';
COMMENT ON COLUMN POTemplateName.description IS 'A brief text about this POTemplateName so the user could know more about it.';

COMMENT ON COLUMN POTemplate.potemplatename IS 'A reference to a POTemplateName row that tells us the name/domain for this POTemplate.';
COMMENT ON COLUMN POTemplate.productrelease IS 'A reference to a ProductRelease from where this POTemplate comes.';
