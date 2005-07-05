/* Notes about integrating ispell with tsearch2, put here so they don't
   get lost. -- StuartBishop 20050531

   Not being used because it doesn't seem to be gaining us anything.
   Might need to generate the .aff and dictfile directly as lexize is
   not doing the stemming as per the documentation
*/

INSERT INTO pg_ts_dict
    (dict_name, dict_comment, dict_initoption, dict_init, dict_lexize)
    (SELECT 'en_GB_ispell',
            'British English ispell',
            'DictFile="/usr/share/dict/british-english",'
            'AffFile="/usr/lib/ispell/british.aff",'
            'StopFile="/usr/share/postgresql/contrib/english.stop"',
            dict_init,
            dict_lexize
    FROM pg_ts_dict
    WHERE dict_name = 'ispell_template');

INSERT INTO pg_ts_dict
    (dict_name, dict_comment, dict_initoption, dict_init, dict_lexize)
    (SELECT 'en_US_ispell',
            'US English ispell',
            'DictFile="/usr/share/dict/american-english",'
            'AffFile="/usr/lib/ispell/american.aff",'
            'StopFile="/usr/share/postgresql/contrib/english.stop"',
            dict_init,
            dict_lexize
    FROM pg_ts_dict
    WHERE dict_name = 'ispell_template');


UPDATE pg_ts_cfgmap SET dict_name='{en_GB_ispell,en_US_ispell,en_stem}'
    where ts_name='default' and dict_name = '{en_stem}';

select lexize('en_GB_ispell', 'program');

