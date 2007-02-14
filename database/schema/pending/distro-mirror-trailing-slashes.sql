UPDATE DistributionMirror SET http_base_url = http_base_url || '/'
WHERE http_base_url IS NOT NULL AND http_base_url NOT LIKE '%/';

UPDATE DistributionMirror SET ftp_base_url = ftp_base_url || '/'
WHERE ftp_base_url IS NOT NULL AND ftp_base_url NOT LIKE '%/';

UPDATE DistributionMirror SET rsync_base_url = rsync_base_url || '/'
WHERE rsync_base_url IS NOT NULL AND rsync_base_url NOT LIKE '%/';

