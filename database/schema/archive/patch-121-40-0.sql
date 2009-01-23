SET client_min_messages=ERROR;

/**********************************************************************
This script should only be run after the bug-190913-gpl-versions branch
has been rolled out to production. Otherwise, it will be possible for
someone to re-add a deprecated license to the ProductLicense table
using the old form.

Below, the ten deprecated licenses are prepended to the
Product.license_info text field. The UPDATE statement's FROM & WHERE
clauses are just necessary to prevent it from updating all the rows,
since they don't all have changes.
**********************************************************************/
UPDATE Product
SET license_info = array_to_string(
        array(
            SELECT
                CASE WHEN license =  60 THEN 'CDDL License'
                     WHEN license =  70 THEN 'CeCILL License'
                     WHEN license = 110 THEN 'Eiffel License'
                     WHEN license = 120 THEN 'GNAT License'
                     WHEN license = 140 THEN 'IBM Public License'
                     WHEN license = 180 THEN 'Open Content License'
                     WHEN license = 240 THEN 'QPL Content License'
                     WHEN license = 250 THEN 'SUN Public License'
                     WHEN license = 260 THEN 'W3C License'
                     WHEN license = 270 THEN 'zlib/libpng License'
                     ELSE ''
                END
            FROM ProductLicense
            WHERE Product.id = ProductLicense.product
                AND ProductLicense.license IN (
                    60, 70, 110, 120, 140, 180, 240, 250, 260, 270)
            ),
        ',\n'
        ) 
        || '.\n' || COALESCE(license_info, '')
FROM ProductLicense
WHERE Product.id = ProductLicense.product
    AND ProductLicense.license IN (
        60, 70, 110, 120, 140, 180, 240, 250, 260, 270);

-- Delete licenses after moving them to Product.license_info.
DELETE FROM ProductLicense
WHERE ProductLicense.license IN (
        60, 70, 110, 120, 140, 180, 240, 250, 260, 270);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 40, 0);
