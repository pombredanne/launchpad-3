// Some Javascript code from Plone Solutions
// http://www.plonesolutions.com, thanks!

/**
 * Launchpad common utilities and functions.
 *
 * @module lp
 * @namespace lp
 */
YUI.add('lp', function(Y) {
    var lp = Y.namespace('lp');

    /**
     * A representation of the launchpad_views cookie.
     *
     * The launchpad_views cookie is used to store the state of optional
     * page content.
     *
     * @class launchpad_views
     */
    lp.launchpad_views = {
        /**
         * Store a value as the named key.
         *
         * @method set
         * @param {String} key the name the value is stored as.
         * @param {string} value the value to store.
         */
        set: function(key, value) {
            var domain = document.location.hostname.replace(
                /.*(launchpad.*)/, '$1');
            var future = new Date();
            future.setYear(future.getFullYear() + 1);
            var config = {
                path: '/',
                domain: domain,
                secure: true,
                expires: future
                };
            Y.Cookie.setSub('launchpad_views', key, value, config);
            },
        /**
         * Retrieve the value in the key.
         *
         * @method get
         * @param {String} key the name the value is stored as.
         * @return {string} the value of the key.
         */
        get: function(key) {
            // The default is true, only values explicitly set to false
            // are false.
            return (Y.Cookie.getSub('launchpad_views', key) != 'false');
            }
    };

    /**
     * Activate all collapsible sections of a page.
     *
     * @method activate_collapsibles
     */
    Y.lp.activate_collapsibles = function() {
        // CSS selector 'legend + *' gets the next sibling element.
        Y.lp.app.widgets.expander.createByCSS(
            '.collapsible', 'legend', 'legend + *', true);
    };

    Y.lp.get_url_path = function(url) {
         return Y.Node.create('<a>junk</a>').set('href', url).get('pathname');
    };
}, "0.1", {"requires":["cookie", "lazr.effects", "lp.app.widgets.expander"]});


// Lint-safe scripting URL.
var VOID_URL = '_:void(0);'.replace('_', 'javascript');


function registerLaunchpadFunction(func) {
    // registers a function to fire onload.
    // Use this for initilaizing any javascript that should fire once the page
    // has been loaded.
    LPS.use('node', function(Y) {
        Y.on('load', function(e) {
            func();
        }, window);
    });
}

// Enable or disable the beta.launchpad.net redirect
function setBetaRedirect(enable) {
    var expire = new Date();
    if (enable) {
        expire.setTime(expire.getTime() + 1000);
        document.cookie = ('inhibit_beta_redirect=0; Expires=' +
                           expire.toGMTString() + cookie_scope);
        alert('Redirection to the beta site has been enabled');
    } else {
        expire.setTime(expire.getTime() + 2 * 60 * 60 * 1000);
        document.cookie = ('inhibit_beta_redirect=1; Expires=' +
                           expire.toGMTString() + cookie_scope);
        alert('You will not be redirected to the beta site for 2 hours');
    }
    return false;
}

function setFocusByName(name) {
    // Focus the first element matching the given name which can be focused.
    var nodes = document.getElementsByName(name);
    for (var i = 0; i < nodes.length; i++) {
        var node = nodes[i];
        if (node.focus) {
            try {
                // Trying to focus a hidden element throws an error in IE8.
                if (node.offsetHeight !== 0) {
                    node.focus();
                }
            } catch (e) {
                LPS.use('console', function(Y) {
                    Y.log('In setFocusByName(<' +
                        node.tagName + ' type=' + node.type + '>): ' + e);
                });
            }
            break;
        }
    }
}

function popup_window(url, name, width, height) {
    var iframe = document.getElementById('popup_iframe_' + name);
    if (!iframe.src || iframe.src == VOID_URL) {
        // The first time this handler runs the window may not have been
        // set up yet; sort that out.
        iframe.style.width = width + 'px';
        iframe.style.height = height + 'px';
        iframe.style.position = 'absolute';
        iframe.style.background = 'white';
        iframe.src = url;
    }
    iframe.style.display = 'inline';
    // I haven't found a way of making the search form focus again when
    // the popup window is redisplayed. I tried doing an
    //    iframe.contentDocument.searchform.search.focus()
    // but nothing happens.. -- kiko, 2007-03-12
}

function selectWidget(widget_name, event) {
  if (event && (event.keyCode == 9 || event.keyCode == 13)) {
      // Avoid firing if user is tabbing through or simply pressing
      // enter to submit the form.
      return;
  }
  document.getElementById(widget_name).checked = true;
}

function switchBugBranchFormAndWhiteboard(id) {
    var div = document.getElementById('bugbranch' + id);
    var wb = document.getElementById('bugbranch' + id + '-wb');

    if (div.style.display == "none") {
        /* Expanding the form */
        if (wb !== null) {
            wb.style.display = "none";
        }
        div.style.display = "block";
        /* Use two focus calls to get the browser to scroll to the end of the
         * form first, then focus back to the first field of the form.
         */
        document.getElementById('field'+id+'.actions.update').focus();
        document.getElementById('field'+id+'.whiteboard').focus();
    } else {
        if (wb !== null) {
            wb.style.display = "block";
        }
        div.style.display = "none";
    }
    return false;
}

function switchSpecBranchFormAndSummary(id) {
    /* The document has two identifiable elements for each
     * spec-branch link:
     *    'specbranchX' which is the div containing the edit form
     *    'specbranchX-summary' which is the div contining the sumary
     * where X is the database id of the link.
     */
    var div = document.getElementById('specbranch' + id);
    var wb = document.getElementById('specbranch' + id + '-summary');

    if (div.style.display == "none") {
        /* Expanding the form */
        if (wb !== null) {
            wb.style.display = "none";
        }
        div.style.display = "block";
        /* Use two focus calls to get the browser to scroll to the end of the
         * form first, then focus back to the first field of the form.
         */
        document.getElementById('field' + id + '.actions.change').focus();
        document.getElementById('field' + id + '.summary').focus();
    } else {
        if (wb !== null) {
            wb.style.display = "block";
        }
        div.style.display = "none";
    }
    return false;
}

function updateField(field, enabled)
{
    field.disabled = !enabled;
}
