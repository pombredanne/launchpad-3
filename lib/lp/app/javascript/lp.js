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
     * Toggle a collapsible's state from open to closed or vice-versa.
     *
     * @method toggle_collapsible
     * @param {Node} collapsible the collapsible to toggle.
     */
    Y.lp.toggle_collapsible = function(collapsible) {
        // Find the collapse icon and wrapper div for this collapsible.
        var icon = collapsible.one('.collapseIcon');

        function get_wrapper_div(node) {
            var wrapper_div = node.one('.collapseWrapper');

            // If either the wrapper or the icon is null, raise an error.
            if (wrapper_div === null) {
                Y.fail("Collapsible has no wrapper div.");
            }
            if (icon === null) {
                Y.fail("Collapsible has no icon.");
            }
            return wrapper_div;
        }
        var wrapper_div = get_wrapper_div(collapsible);

        // Work out the target icon and animation based on the state of
        // the collapse wrapper. We ignore the current state of the icon
        // because the collapse wrapper is the canonical guide as to
        // whether the item is collapsed or expanded. This saves us from
        // situations where we end up using the wrong icon for a given
        // state.
        var target_icon;
        var target_anim;
        var expanding;
        if (wrapper_div.hasClass('lazr-closed')) {
            // The wrapper is collapsed; expand it and collapse all its
            // siblings if it's in an accordion.
            expanding = true;
            target_anim = Y.lazr.effects.slide_out(wrapper_div);
            target_icon = "/@@/treeExpanded";
        } else {
            // The wrapper is open; just collapse it.
            expanding = false;
            target_anim = Y.lazr.effects.slide_in(wrapper_div);
            target_icon = "/@@/treeCollapsed";
        }

        // Run the animation and set the icon src correctly.
        target_anim.run();
        icon.set('src', target_icon);

        // Work out if the collapsible is in an accordion and process
        // the siblings accordingly if the current collapsible is being
        // expanded.
        var parent_node = collapsible.get('parentNode');
        var in_accordion = parent_node.hasClass('accordion');
        if (in_accordion && expanding) {
            var sibling_target_icon = "/@@/treeCollapsed";
            Y.each(parent_node.all('.collapsible'), function(sibling) {
                // We only actually collapse the sibling if it's not our
                // current collapsible.
                if (sibling != collapsible) {
                    var sibling_wrapper_div = get_wrapper_div(sibling);
                    var sibling_icon = sibling.one('.collapseIcon');
                    var sibling_target_anim = Y.lazr.effects.slide_in(
                        sibling_wrapper_div);
                    sibling_target_anim.run();
                    sibling_icon.set('src', sibling_target_icon);
                }
            });
        }
    };

    /**
     * Activate all collapsible sections of a page.
     *
     * @method activate_collapsibles
     */
    Y.lp.activate_collapsibles = function() {
        // Grab the collapsibles.
        Y.all('.collapsible').each(function(collapsible) {

            // Try to grab the legend in the usual way.
            var legend = collapsible.one('legend');
            if (legend === null) {
                // If it's null, this might be a collapsible div, not fieldset,
                // so try to grap the div's "legend".
                legend = collapsible.one('.config-options');
            }
            if (legend === null ||
                legend.one('.collapseIcon') !== null) {
                // If there's no legend there's not much we can do,
                // so just exit this iteration. If there's a
                // collapseIcon in there we consider the collapsible
                // to already have been set up and therefore ignore
                // it this time around.
                return;
            }

            var icon = Y.Node.create(
                '<img src="/@@/treeExpanded" class="collapseIcon" />');

            // We use javascript:void(0) here (though it will cause
            // lint to complain) because it prevents clicking on the
            // anchor from altering the page URL, which can subtly
            // break things.
            var anchor = Y.Node.create(
                '<a href="javascript:void(0);"></a>');
            anchor.appendChild(icon);

            // Move the contents of the legend into the span. We use
            // the verbose version of <span /> to avoid silly
            // breakages in Firefox.
            var span = Y.Node.create('<span></span>');
            var legend_children = legend.get('children');
            var len;

            if (Y.Lang.isValue(legend_children)) {
                // XXX 2009-07-06 gmb Account for oddness from
                // Node.get('children'); (see YUI ticket 2528028 for
                // details).
                len = legend_children.size ?
                    legend_children.size() : legend_children.length;
            } else {
                len = 0;
            }

            if (len > 0) {
                // If the legend has child elements, move them
                // across one by one.
                Y.each(legend_children, function(child_node) {
                    if (child_node.get('tagName') == 'A') {
                        // If this child is an anchor, add only its
                        // contents to the span.
                        new_node = Y.Node.create(
                            child_node.get('innerHTML'));
                        span.appendChild(new_node);
                        legend.removeChild(child_node);
                    } else {
                        // Otherwise, add the node to the span as it
                        // is.
                        span.appendChild(child_node);
                    }
                });
            } else {
                // Otherwise just move the innerHTML across as a
                // block. Once the span is appended to the anchor,
                // this will essentially turn the contents of the
                // legend into a link.
                span.set('innerHTML', legend.get('innerHTML'));
                legend.set('innerHTML', '');
            }

            // Replace the contents of the legend with the anchor.
            anchor.appendChild(span);
            legend.appendChild(anchor);

            // Put a wrapper around the fieldset contents for ease
            // of hiding.
            var wrapper_div = Y.Node.create(
                '<div class="collapseWrapper" />');

            // Loop over the children of the collapsible and move them
            // into the wrapper div. We remove the legend from the
            // collapsible at this point to make sure it gets left
            // outside the wrapper div; we'll add it again later.
            collapsible.removeChild(legend);

            // "Why do this as a while?" I hear you cry. Well, it's
            // because using Y.each() leads to interesting results
            // in FF3.5, Opera and Chrome, since by doing
            // appendChild() with each child node (and thus removing
            // them from the collapsible) means you're altering the
            // collection as you're looping over it, which is a Bad
            // Thing. This isn't as pretty but it actually works.
            var first_child = collapsible.one(':first-child');
            while (Y.Lang.isValue(first_child)) {
                wrapper_div.appendChild(first_child);
                first_child = collapsible.one(':first-child');
            }

            // Put the legend and the new wrapper div into the
            // collapsible in the right order.
            collapsible.appendChild(legend);
            collapsible.appendChild(wrapper_div);

            // If the collapsible is to be collapsed on pageload, do
            // so.
            if (collapsible.hasClass('collapsed')) {
                // Strip out the 'collapsed' class as it's no longer
                // needed.
                collapsible.removeClass('collapsed');

                // We use the slide_in effect to hide the
                // collapsible because it sets up all the properties
                // and classes for the element properly and saves us
                // from embarrasment later on.
                var slide_in = Y.lazr.effects.slide_in(wrapper_div);
                slide_in.run();

                icon.set('src', '/@@/treeCollapsed');
            }

            // Finally, add toggle_collapsible() as an onclick
            // handler to the anchor.
            anchor.on('click', function(e) {
                Y.lp.toggle_collapsible(collapsible);
            });
        });
    };

}, "0.1", {"requires":["cookie", "lazr.effects"]});


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

function toggleExpandableTableRow(element_id) {
    var row = document.getElementById(element_id);
    var view_icon = document.getElementById(element_id + "-arrow");
    if (row.style.display == "table-row") {
      row.style.display = "none";
      view_icon.setAttribute("src", "/@@/treeCollapsed");
    } else {
      row.style.display = "table-row";
      view_icon.setAttribute("src", "/@@/treeExpanded");
    }
    return false;
}

function toggleExpandableTableRows(class_name) {
    var view_icon = document.getElementById(class_name + "-arrow");
    var all_page_tags = document.getElementsByTagName("*");
    for (i = 0; i < all_page_tags.length; i++) {
        row = all_page_tags[i];
        if (row.className == class_name) {
            if (row.style.display == "table-row") {
              row.style.display = "none";
              view_icon.setAttribute("src", "/@@/treeCollapsed");
            } else {
              row.style.display = "table-row";
              view_icon.setAttribute("src", "/@@/treeExpanded");
            }
        }
    }
    return false;
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
