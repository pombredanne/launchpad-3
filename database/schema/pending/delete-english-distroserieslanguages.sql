-- Delete English DistroSeriesLanguage. They should
-- not exist since English is not translatable.
-- Note that the table has the old name.
DELETE FROM 
    DistroReleaseLanguage
USING 
    Language
WHERE
    DistroReleaseLanguage.language = Language.id
    AND Language.code = 'en';