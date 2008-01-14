import re
from pyPgSQL import PgSQL
from string import split, join

# LaunchPad Dependencies
from canonical.foaf.nickname import generate_nick
from canonical.encoding import guess as ensure_unicode

def data_sanitizer(data):
    if not data:
        return data
    try:
        # check that this is unicode data
        data.decode("utf-8").encode("utf-8")
        return data
    except UnicodeError:
        # check that this is latin-1 data
        s = data.decode("latin-1").encode("utf-8")
        s.decode("utf-8")
        return s
    #zope facility that doesn't work very well
    #return ensure_unicode(data)

class SQLThing:
    def __init__(self, pghost, dbname):
        self.dbname = dbname
        self.pghost = pghost
        self.db = PgSQL.connect(host=self.pghost, database=self.dbname)

    def commit(self):
        return self.db.commit()

    def close(self):
        return self.db.close()

    def _get_dicts(self, cursor):
        names = [x[0] for x in cursor.description]
        ret = []
        for item in cursor.fetchall():
            res = {}
            for i in range(len(names)):
                res[names[i]] = item[i]
            ret.append(res)
        return ret

    def _query_to_dict(self, query, args=None):
        cursor = self._exec(query, args)
        return self._get_dicts(cursor)

    def _query(self, query, args=None):
        #print repr(query), repr(args)
        cursor = self.db.cursor()
        cursor.execute(query, args or [])
        results = cursor.fetchall()
        return results

    def _query_single(self, query, args=None):
        q = self._query(query, args)
        if len(q) == 1:
            return q[0]
        elif not q:
            return None
        else:
            raise AssertionError, "%s killed us on %s %s" \
                % (len(q), query, args)

    def _exec(self, query, args=None):
        #print repr(query), repr(args)
        cursor = self.db.cursor()
        cursor.execute(query, args or [])
        return cursor

    def _insert(self, table, data):
        keys = data.keys()
        query = "INSERT INTO %s (%s) VALUES (%s)" \
                 % (table, ",".join(keys), ",".join(["%s"] * len(keys)))
        try:
            self._exec(query, data.values())
        except:
            print "Bad things happened, data was %s" % data
            raise

    def _update(self, table, data, clause):
        fieldstring = ''
        for key, value in data.items():
            if value:
                value = value.replace("'", "")
                fieldstring += """ %s='%s',""" % (key, value)

        ## delete the last ','
        fieldstring = fieldstring[:-1]

        if not fieldstring:
            print '@\tNo info to UPDATE'
            return

        query = "UPDATE %s SET %s WHERE %s;" % (table, fieldstring, clause)
        try:
            self._exec(query)
            #print query
        except:
            print "Bad things happened, data was %s" % data
            raise

# XXX: cprov 2005-01-26:
# This class needs a lot of Love, it is fitting and cleaning data
# for the DB backend classes
class FitData(object):
    pdisplayname = None
    pemail = None
    name = None
    displayname = None
    title = None
    summary = None
    description = None
    homepage = None
    screenshot = None
    wiki = None
    listurl = None
    download = None
    sourceforgeproject = None
    freshmeatproject = None
    plang = None

    def __init__(self, data, name):
        # XXX cprov 2005-01-26:
        # If no data is available Create an Empty Product
        if not data:
            self.name = name
            self.displayname = name
            self.title = name
            self.summary = 'No Summary Available'
            self.description = 'No Description Available'
            return

        # XXX cprov 2005-01-26:
        # Both have devels strange shit with wrong encode keys
        # multiple devels and so
        try:
            self.pdisplayname = data_sanitizer(data['devels'].keys()[0])
            self.pemail = data_sanitizer(data['devels'].values()[0])
        except KeyError:
            print '@\tNo Devel'
        except IndexError:
            print '@\tNo Devel'

        ## both have project
        self.name = data_sanitizer(data['product']).split()[0].lower()

        ## only SF has projectname
        if 'productaname' in data.keys():
            self.displayname = data_sanitizer(data['productname'])
            self.title = data_sanitizer(data['productname'])
        else:
            ## try to improve it
            self.displayname = data_sanitizer(data['product'])
            self.title = data_sanitizer(data['product'])

        ## both have summary
        if 'summary' in data.keys():
            self.summary = data_sanitizer(data['summary'])
        else:
            self.summary = data_sanitizer(data['description']).split(".")[0]
            self.summary += '.'

        ## both have description
        self.description = data_sanitizer(data['description'])

        ## both have homepage
        try:
            self.homepage = data_sanitizer(data['homepage'])
        except KeyError:
            pass
        ## support several plangs
        try:
            plang_list = data['programminglang']
            temp_plang = ''
            for plang in plang_list:
                temp_plang += ' ' + plang

            plang = data_sanitizer(temp_plang)
        except KeyError:
            pass

        try:
            screenshot = data_sanitizer(data['screenshot'])
        except KeyError:
            pass

        ## we cannot support several lists
        try:
            listurl = data_sanitizer(data['list'][0])
        except KeyError:
            listurl = None
        except IndexError:
            listurl = None


        if 'sf' in data.keys():
            self.sourceforgeproject = data_sanitizer(data['sf'])
        else:
            self.sourceforgeproject = None

        if 'fm' in data.keys():
            self.freshmeatproject = data_sanitizer(data['fm'])
        else:
            self.freshmeatproject = None


class Doap(SQLThing):
    #
    # SourcePackageName
    #

    def getPackaging(self, product_id, package_id):
        return self._query_single("""SELECT * FROM Packaging
        WHERE product = %s AND sourcepackage = %s""",
                                  (product_id, package_id))

    def getSourcePackageByName(self, name, distroname):
        # XXX cprov 2005-01-26:
        # If distroname wasn't provided use Ubuntu.
        if not distroname:
            distroname = 'ubuntu'

        return self._query_single("""SELECT SourcePackage.id
            FROM SourcePackage,SourcePackagename,Distribution
            WHERE SourcePackage.distro = Distribution.id AND
            SourcePackage.sourcepackagename = SourcePackageName.id AND
            Distribution.name = %s AND
            SourcePackageName.name = %s;""", (distroname, name,))

    def getSourcePackageName(self, name):
        return self._query_single("""SELECT id FROM sourcepackagename
                                     WHERE name = %s;""", (name,))

    def getSourcePackageNames(self):
        return self._query_to_dict("""SELECT name FROM sourcepackagename;""")

    def getPersonByEmail(self, email):
        return self._query_single("""SELECT
            Person.id FROM Person,emailaddress
            WHERE email = %s AND
            Person.id = emailaddress.person;""", (email,))

    def getPersonByName(self, name):
        return self._query_single("""SELECT Person.id FROM Person
                                     WHERE name = %s""", (name,))

    def createPerson(self, name, email):
        print "@\tCreating Person %s <%s>" % (name, email)
        name = data_sanitizer(name)

        #XXX: cprov 2005-01-26:
        # It shouldn't be here.
        email = email.replace("__dash__", "")
        email = email.replace("|dash|", "")
        email = email.replace("[dash]", "")
        email = email.replace(" ", "")

        items = name.split()
        if len(items) == 1:
            givenname = name
            familyname = ""
        else:
            givenname = items[0]
            familyname = " ".join(items[1:])

        data = {
            "displayname":  name,
            "givenname":    givenname,
            "familyname":   familyname,
            "name":         generate_nick(email, self.getPersonByName),
        }
        self._insert("person", data)
        pid = self._query_single("SELECT CURRVAL('person_id_seq')")[0]
        self.createEmail(pid, email)

    def createEmail(self, pid, email):
        data = {
            "email":    email,
            "person":   pid,
            "status":   1, # Status 'New'
        }
        self._insert("emailaddress", data)

    def ensurePerson(self, displayname, email):
        person = self.getPersonByEmail(email)
        if person:
            return person
        # we will create a new person
        self.createPerson(displayname, email)
        return self.getPersonByEmail(email)

    def getProductByName(self, name):
        return self._query_single("""SELECT * FROM product WHERE name=%s;""",
                                  name)

    # XXX: cprov 2005-01-26:
    # Try to return the right project name (reviewed sf/fm one)
    # not the DOAP name.
    def getProductsForUpdate(self):
        products = self._query("""SELECT name FROM product WHERE
                                  autoupdate=True AND reviewed=True;""")
        return len(products), [product[0] for product in products]

    def getProductSeries(self, product, name):
        return self._query_single("""SELECT * FROM productseries WHERE
        name=%s AND product=%s;""", (name, product))

    def updateProduct(self, data, productname):
        ## if there is no data available simply return
        if not data:
            print '@\t No data available for Update'
            return

        fit = FitData(data, productname)

        # only update peripheral data, rather than the summary and
        # description, when we are in update mode.
        dbdata = {"homepageurl":         fit.homepage,
                  "screenshotsurl":      fit.screenshot,
                  "listurl":             fit.listurl,
                  "downloadurl":         fit.download,
                  "programminglang":     fit.plang,
                  "sourceforgeproject":  fit.sourceforgeproject,
                  "freshmeatproject":    fit.freshmeatproject
                }

        # the query reinforces the requirement that we only update when the
        # autoupdate field is true
        self._update("product", dbdata, ("name='%s' and autoupdate=True"
                                         % productname))
        print '@\tProduct %s Updated' % productname


    def createProduct(self, owner, fitted_data):

        fit = fitted_data

        datecreated = 'now()'

        # XXX: cprov 2004-10-15:
        # Missed lastdoap field (product+lastdoap)
        dbdata = {"owner":               owner,
                  "name" :               fit.name,
                  "displayname":         fit.displayname,
                  "title":               fit.title,
                  "summary":             fit.summary,
                  "description":         fit.description,
                  "datecreated":         datecreated,
                  "homepageurl":         fit.homepage,
                  "screenshotsurl":      fit.screenshot,
                  "listurl":             fit.listurl,
                  "programminglang":     fit.plang,
                  "downloadurl":         fit.download,
                  "sourceforgeproject":  fit.sourceforgeproject,
                  "freshmeatproject":    fit.freshmeatproject,
                  }

        self._insert("product", dbdata)
        print '@\tProduct %s created' % fit.displayname

    def createProductRole(self, owner, product, role):
        dbdata = { "person":  owner,
                   "product": product,
                   "role": role,
                   }

        self._insert("productrole", dbdata)
        print '@\tProduct Role %s Created' % role

    def createProductSeries(self, product, name, displayname, summary):
        dbdata = {"product":     product,
                  "name":        name,
                  "summary":     summary,
                  "displayname": displayname,
                  }

        self._insert("productseries", dbdata)
        print '@\tProduct Series %s Created' % displayname

    def ensureProduct(self, data, productname, ownername=None):

        if self.getProductByName(productname):
            self.updateProduct(data, productname)
            return

        ## Fits the data (sanitizer, multiple entries handling, clean-up, etc)
        fit = FitData(data, productname)

        # XXX cprov 2005-01-26:
        # Problems with wierd developers name and/or email
        if fit.pdisplayname and fit.pemail:
            owner = self.ensurePerson(fit.pdisplayname, fit.pemail)[0]
        else:
            print "@\tDOAP wins a Product "
            owner = self.getPersonByName(ownername)[0]


        ## Create a product based on fitted data
        self.createProduct(owner, fit)

        ## Get the 'just inserted' product id
        product = self.getProductByName(fit.name)[0]
        # XXX cprov 2005-01-26:
        # Hardcoded Role too Member
        role = 1

        ## create productrole
        self.createProductRole(owner, product, role)

        ## productseries

        # XXX: cprov 2004-10-12
        # Hardcoded Product Series Name as "head" (series+name).
        name = 'head'
        # XXX: cprov 2004-10-12
        # Displayname composed by projectname-serie as
        # apache-1.2 or Mozilla-head (series+diaplyname).
        displayname = fit.displayname + ' Head'

        summary = """This is the primary HEAD branch of the mainline
        revision control system for %s. Releases on this
        series are usually development milestones and test
        releases.""" % fit.displayname

        self.createProductSeries(product, name, displayname, summary)


    def ensurePackaging(self, productname, packagename, distroname):

        product = self.getProductByName(productname)

        if product:
            product_id = product[0]
        else:
            ## Aborting !!!
            print '@ %s Product not Found !!!!' % productname
            return

        sourcepackage = self.getSourcePackageByName(packagename, distroname)

        if not sourcepackage:
            ## Aborting !!!
            return

        package_id = sourcepackage[0]

        ## verify the respective packaging entry
        if self.getPackaging(product_id, package_id):
            print '@\tPackaging Entry Found'
            return True

        # XXX: daniels 2004-12-14: hardcoded Prime Packaging.
        packaging = 1

        dbdata = { "product" : product_id,
                   "sourcepackage": package_id,
                   "packaging": packaging,
                   }

        self._insert("packaging", dbdata)
        print '@\tPackaging %s - %s Created' % (productname, packagename)
        # finished with success
        return True

