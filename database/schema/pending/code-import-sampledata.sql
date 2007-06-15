DELETE FROM CodeImport;

INSERT INTO CodeImport (branch, registrant, rcs_type, svn_branch_url, review_status)
       (SELECT branch.id, person.id, 2, 'http://svn.example.org/svnroot/gnome-terminal/trunk', 20
        FROM product
        JOIN branch on branch.product = product.id
        JOIN person on person.name='no-priv'
        WHERE product.name='gnome-terminal' and branch.url like '%main');

INSERT INTO CodeImport (branch, registrant, rcs_type, cvs_root, cvs_module)
       (SELECT series.import_branch, person.id, 1, series.cvsroot, series.cvsmodule
        FROM productseries as series
        JOIN person on person.name='no-priv'
        JOIN product on series.product=product.id
        WHERE product.name='evolution' AND series.name='trunk');
