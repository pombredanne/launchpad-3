SET client_min_messages=ERROR;

-- Migrate all POFile.path to a safe value if there athey are just using a path + language code.
CREATE OR REPLACE FUNCTION get_right_path(text, text, text, text) RETURNS text AS
$$
import os.path

if args[3] is None:
    locale = args[2]
else:
    locale = '%s@%s' % (args[2], args[3])

path = os.path.dirname(args[0])
templatename = os.path.basename(args[0]).rsplit('.', 1)[0]

return os.path.join(path, '%s-%s.po' % (templatename, locale))
$$ LANGUAGE plpythonu IMMUTABLE;

UPDATE POFile
SET path=(SELECT get_right_path(POTemplate.path, POFile.path, language.code, POFile.variant))
FROM Language, POTemplate
WHERE POFile.language = Language.id AND POFile.potemplate = POTemplate.id AND
    EXISTS (
        SELECT pf.id
        FROM POFile pf, POTemplate pt
        WHERE
            POTemplate.distrorelease = pt.distrorelease AND
            POTemplate.sourcepackagename = pt.sourcepackagename AND
            POTemplate.productseries = pt.productseries AND
            POTemplate.id = pf.potemplate AND
            POFile.language = pf.language AND
            POFile.variant = pf.variant AND
            POFile.id <> pf.id);
DROP FUNCTION get_right_path(text, text, text, text);
