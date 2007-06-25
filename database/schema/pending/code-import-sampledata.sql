DELETE FROM CodeImport;

DELETE FROM Branch where name = 'import';

INSERT INTO Branch (name, owner, product, url, title)
       (SELECT 'import', person.id, product.id, NULL, 'GNOME Terminal Import Branch'
       FROM person, product
       WHERE person.name = 'vcs-imports' AND product.name='gnome-terminal');

INSERT INTO Branch (name, owner, product, url, title)
       (SELECT 'import', person.id, product.id, NULL, 'Evolution Import Branch'
       FROM person, product
       WHERE person.name = 'vcs-imports' AND product.name='evolution');

INSERT INTO CodeImport (id, branch, registrant, rcs_type, svn_branch_url, review_status)
       (SELECT 1, branch.id, np.id, 2, 'http://svn.example.org/svnroot/gnome-terminal/trunk', 20
        FROM product
        JOIN person np on np.name='no-priv'
        JOIN person vcs on vcs.name='vcs-imports'
        JOIN branch on branch.product = product.id and branch.owner = vcs.id and branch.name='import'
        WHERE product.name='gnome-terminal');

INSERT INTO CodeImport (id, branch, registrant, rcs_type, cvs_root, cvs_module)
       (SELECT 2, branch.id, np.id, 1, ':pserver:anonymous@anoncvs.example.org:/cvs/gnome', 'evolution'
        FROM productseries as series
        JOIN person as np on np.name='no-priv'
        JOIN person as vcs on vcs.name='vcs-imports'
        JOIN product on product.name='evolution'
        JOIN branch on branch.product = product.id and branch.owner = vcs.id and branch.name='import'
        WHERE series.product=product.id and series.name='trunk');
