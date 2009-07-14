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
        var icon = collapsible.query('.collapseIcon');
        var wrapper_div = collapsible.query('.collapseWrapper');

        // If either the wrapper or the icon is null, raise an error.
        if (wrapper_div === null) {
            Y.fail("Collapsible has no wrapper div.");
        }
        if (icon === null) {
            Y.fail("Collapsible has no icon.");
        }

        // Work out the target icon and animation based on the state of
        // the collapse wrapper. We ignore the current state of the icon
        // because the collapse wrapper is the canonical guide as to
        // whether the item is collapsed or expanded. This saves us from
        // situations where we end up using the wrong icon for a given
        // state.
        var target_icon;
        var target_anim;
        if (wrapper_div.hasClass('lazr-closed')) {
            // The wrapper is collapsed.
            target_anim = Y.lazr.effects.slide_out(wrapper_div);
            target_icon = "/@@/treeExpanded";
        } else {
            // The wrapper is open.
            target_anim = Y.lazr.effects.slide_in(wrapper_div);
            target_icon = "/@@/treeCollapsed";
        }

        // Run the animation and set the icon src correctly.
        target_anim.run();
        icon.set('src', target_icon);
    };

    /**
     * Activate all collapsible sections of a page.
     *
     * @method activate_collapsibles
     */
    Y.lp.activate_collapsibles = function() {
        // Grab the collapsibles.
        var collapsibles = Y.all('.collapsible');
        if (collapsibles !== null) {
            Y.each(collapsibles, function(collapsible) {
                var legend = collapsible.query('legend');
                if (legend === null ||
                    legend.query('.collapseIcon') !== null) {
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
                var first_child = collapsible.query(':first-child');
                while (Y.Lang.isValue(first_child)) {
                    wrapper_div.appendChild(first_child);
                    first_child = collapsible.query(':first-child');
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
        }
    };

}, '0.1', {requires:['cookie', 'lazr.effects']});


// Lint-safe scripting URL.
var VOID_URL = '_:void(0);'.replace('_', 'javascript');


function registerLaunchpadFunction(func) {
    // registers a function to fire onload.
    // Use this for initilaizing any javascript that should fire once the page
    // has been loaded.
    YUI().use('node', function(Y) {
        Y.on('load', function(e) {
            func();
        }, window);
    });
}

function getContentArea() {
    // to end all doubt on where the content sits. It also felt a bit
    // silly doing this over and over in every function, even if it is
    // a tiny operation. Just guarding against someone changing the
    // names again, in the name of semantics or something.... ;)
    var node = document.getElementById('maincontent');
    if (!node) {node = $('content');}
    if (!node) {node = $('mainarea');}
    return node;
}

function toggleCollapsible(e) {
    // this is the function that collapses/expands fieldsets.

    // "this" is the node that the event is attached to
    var node = this;

    // walk up the node hierarchy until we find the <legend> element
    while (node.nodeName.toLowerCase() != 'legend') {
        node = node.parentNode;
        if (!node) {
            return false;
        }
    }

    // the expander image is legend -> a -> img
    var icon = node.firstChild.firstChild;
    var legend = node;

    if (icon.getAttribute('src').indexOf('/@@/treeCollapsed') != -1) {
        // that was an ugly check, but IE rewrites image sources to
        // absolute urls from some sick reason....
        icon.setAttribute('src','/@@/treeExpanded');
        swapElementClass(
            legend.parentNode.lastChild, 'collapsed', 'expanded');
        swapElementClass(
            legend.parentNode.childNodes[1], 'expanded', 'collapsed');
    } else {
        icon.setAttribute('src','/@@/treeCollapsed');
        swapElementClass(
            legend.parentNode.lastChild, 'expanded', 'collapsed');
        swapElementClass(
            legend.parentNode.childNodes[1], 'collapsed', 'expanded');
    }
    return false;
}

function activateCollapsibles() {
    // a script that searches for sections that can be (or are
    // already) collapsed - and enables the collapse-behavior

    // usage : give the class "collapsible" to a fieldset also, give
    // it a <legend> with some descriptive text.  you can also add the
    // class "collapsed" amounting to a total of
    // <fieldset class="collapsible collapsed"> to make the section
    // pre-collapsed

    // terminate if we hit a non-compliant DOM implementation
    if (!document.getElementsByTagName) {
        return false;
    }
    if (!document.getElementById) {
        return false;
    }

    // only search in the content-area
    var contentarea = getContentArea();
    if (!contentarea) {
        return false;
    }

    // gather all objects that are to be collapsed
    // we only do fieldsets for now. perhaps DIVs later...
    var collapsibles = contentarea.getElementsByTagName('fieldset');

    for (var i = 0; i < collapsibles.length; i++) {
        if (collapsibles[i].className.indexOf('collapsible') == -1) {
            continue;
        }

        var legends = collapsibles[i].getElementsByTagName('LEGEND');

        // get the legend
        // if there is no legend, we do not touch the fieldset at all.
        // we assume that if there is a legend, there is only
        // one. nothing else makes any sense
        if (!legends.length) {
            continue;
        }
        var legend = legends[0];

        //create an anchor to handle click-events
        var anchor = document.createElement('a');
        anchor.href = '#';
        anchor.onclick = toggleCollapsible;

        // add the icon/button with its functionality to the legend
        var icon = document.createElement('img');
        icon.setAttribute('src','/@@/treeExpanded');
        icon.setAttribute('class','collapseIcon');
        icon.setAttribute('height','14');
        icon.setAttribute('width','14');

        // insert the icon icon at the start of the anchor
        anchor.appendChild(icon);

        // reparent all the legend's children into a span, and the span
        // into an anchor. The span is used to underline the legend
        // text; because the img is inside the anchor, we can't
        // underline the whole anchor.
        var span = document.createElement('span');
        while (legend.hasChildNodes()) {
            var child = legend.firstChild;
            legend.removeChild(child);
            span.appendChild(child);
        }
        anchor.appendChild(span);

        // add the anchor to the legend
        legend.appendChild(anchor);

        // wrap the contents inside a div to make turning them on and
        // off simpler.  unless something very strange happens, this
        // new div should always be the last childnode we'll give it a
        // class to make sure.

        var hiderWrapper = document.createElement('div');
        hiderWrapper.setAttribute('class','collapseWrapper');

        // also add a new div describing that the element is collapsed.
        var collapsedDescription = document.createElement('div');
        collapsedDescription.setAttribute('class','collapsedText');
        collapsedDescription.style.display = 'none';

        // if the fieldset has the class of "collapsed", pre-collapse
        // it. This can be used to preserve valuable UI-space
        if (collapsibles[i].className.indexOf('collapsed') != -1 ) {
            icon.setAttribute('src','/@@/treeCollapsed');
            collapsedDescription.style.display = 'block';
            setElementClass(hiderWrapper, 'collapsed');
            // Unhide the fieldset, now that all of its children are hidden:
            removeElementClass(collapsibles[i], 'collapsed');
        }

        // now we have the wrapper div.. Stuff all the contents inside it
        var nl = collapsibles[i].childNodes.length;
        for (var j = 0; j < nl; j++){
            var node = collapsibles[i].childNodes[0];
            if (node.nodeName == 'LEGEND') {
                if (collapsibles[i].childNodes.length > 1) {
                    hiderWrapper.appendChild(collapsibles[i].childNodes[1]);
                }
            } else {
                hiderWrapper.appendChild(collapsibles[i].childNodes[0]);
            }
        }
        // and add it to the document
        collapsibles[i].appendChild(hiderWrapper);
        collapsibles[i].insertBefore(collapsedDescription, hiderWrapper);
    }
}

function toggleFoldable(e) {
    var ELEMENT_NODE = 1;
    var node = this;
    while (node.nextSibling) {
        node = node.nextSibling;
        if (node.nodeType != ELEMENT_NODE) {
            continue;
        }
        if (node.className.indexOf('foldable') == -1) {
            continue;
        }
        if (node.style.display == 'none') {
            node.style.display = 'inline';
        } else {
            node.style.display = 'none';
        }
    }
}

function activateFoldables() {
    // Create links to toggle the display of foldable content.
    var included = getElementsByTagAndClassName(
        'span', 'foldable', document);
    var quoted = getElementsByTagAndClassName(
        'span', 'foldable-quoted', document);
    var elements = concat(included, quoted);
    for (var i = 0; i < elements.length; i++) {
        var span = elements[i];
        if (span.className == 'foldable-quoted') {
            var quoted_lines = span.getElementsByTagName('br');
            if (quoted_lines && quoted_lines.length <= 11) {
                // We do not hide short quoted passages (12 lines) by default.
                continue;
            }
        }

        var ellipsis = document.createElement('a');
        ellipsis.style.textDecoration = 'underline';
        ellipsis.href = VOID_URL;
        ellipsis.onclick = toggleFoldable;
        ellipsis.appendChild(document.createTextNode('[...]'));

        span.parentNode.insertBefore(ellipsis, span);
        span.insertBefore(document.createElement('br'), span.firstChild);
        span.style.display = 'none';
        if (span.nextSibling) {
            // Text lines follows this span.
            var br = document.createElement('br');
            span.parentNode.insertBefore(br, span.nextSibling);
        }
    }
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
            node.focus();
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


function convertTextInputToTextArea(text_input_id, rows) {
    var current_text_input = getElement(text_input_id);
    var new_text_area = document.createElement("textarea");
    var attributes = {
        'id': text_input_id,
        'rows': rows,
        'name': getNodeAttribute(current_text_input, 'name'),
        'lang': getNodeAttribute(current_text_input, 'lang'),
        'dir': getNodeAttribute(current_text_input, 'dir')
    };

    updateNodeAttributes(new_text_area, attributes);

    // we set the javascript events because updateNodeAttributes gets confused
    // with those events, because it says that 'event' is not defined. 'event'
    // is one of the arguments of the javascript call that is being copied.
    new_text_area.setAttribute(
        'onKeyPress', getNodeAttribute(current_text_input, 'onkeypress'));
    new_text_area.setAttribute(
        'onChange', getNodeAttribute(current_text_input, 'onchange'));
    new_text_area.value = current_text_input.value;
    swapDOM(current_text_input, new_text_area);
    return new_text_area;
}


function upgradeToTextAreaForTranslation(text_input_id) {
    var rows = 6;
    var current_text_input = $(text_input_id);
    var text_area = convertTextInputToTextArea(text_input_id, rows);
    text_area.focus();
}

function insertExpansionButton(expandable_field) {
    var button = createDOM(
        'button', {
            'style': 'padding: 0;',
            'title': 'Makes the field larger, so you can see more text.'
        }
    );
    var icon = createDOM(
        'img', {
            'alt': 'Enlarge Field',
            'src': '/+icing/translations-add-more-lines.gif'
        }
    );
    appendChildNodes(button, icon);
    function buttonOnClick(e) {
        upgradeToTextAreaForTranslation(expandable_field.id);
        e.preventDefault();
        removeElement(button);
        return false;
    }
    connect(button, 'onclick', buttonOnClick);
    insertSiblingNodesAfter(expandable_field, button);
}

function insertAllExpansionButtons() {
    var expandable_fields = getElementsByTagAndClassName(
        'input', 'expandable');
    forEach(expandable_fields, insertExpansionButton);
}

function unescapeHTML(unescaped_string) {
    // Based on prototype's unescapeHTML method.
    // See launchpad bug #78788 for details.
    var div = document.createElement('div');
    div.innerHTML = unescaped_string;
    return div.childNodes[0] ? div.childNodes[0].nodeValue : '';
}

function copyInnerHTMLById(from_id, to_id) {
    var from = getElement(from_id);
    var to = getElement(to_id);

    // The replacement regex strips all tags from the html.
    to.value = unescapeHTML(from.innerHTML.replace(/<\/?[^>]+>/gi, ""));

}

function writeTextIntoPluralTranslationFields(from_id,
                                              to_id_pattern, nplurals) {
    // skip when x is 0, as that is the singular
    for (var x = 1; x < nplurals; x++) {
        var to_id = to_id_pattern + x + "_new";
        copyInnerHTMLById(from_id, to_id);
    }
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

function activateConstrainBugExpiration() {
    // Constrain enable_bug_expiration to the Launchpad Bugs radio input.
    // The Launchpad bug tracker is either the first item in a product's
    // bugtracker field, or it is a distribution's official_malone field.
    var bug_tracker_input = getElement('field.bugtracker.0');
    if (! bug_tracker_input) {
        bug_tracker_input = getElement('field.official_malone');
    }
    var bug_expiration_input = getElement('field.enable_bug_expiration');
    if (! bug_tracker_input || ! bug_expiration_input) {
        return;
    }
    // Disable enable_bug_expiration onload if Launchpad is not the
    // bug tracker.
    if (! bug_tracker_input.checked) {
        bug_expiration_input.disabled = true;
    }
    constraint = function (e) {
        if (bug_tracker_input.checked) {
            bug_expiration_input.disabled = false;
            bug_expiration_input.checked = true;
        } else {
            bug_expiration_input.checked = false;
            bug_expiration_input.disabled = true;
        }
    };
    var inputs = document.getElementsByTagName('input');
    for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].name == 'field.bugtracker' ||
            inputs[i].name == 'field.official_malone') {
            inputs[i].onclick = constraint;
        }
    }
}

function updateField(field, enabled)
{
    field.disabled = !enabled;
}


function collapseRemoteCommentReply(comment_index) {
    var prefix = 'remote_comment_reply_';
    $(prefix + 'tree_icon_' + comment_index).src = '/@@/treeCollapsed';
    $(prefix + 'div_' + comment_index).style.display = 'none';
}

function expandRemoteCommentReply(comment_index) {
    var prefix = 'remote_comment_reply_';
    $(prefix + 'tree_icon_' + comment_index).src = '/@@/treeExpanded';
    $(prefix + 'div_' + comment_index).style.display = 'block';
}

function toggleRemoteCommentReply(comment_index) {
    var imgname = $('remote_comment_reply_tree_icon_' + comment_index)
      .src.split('/')
      .pop();
    var expanded = (imgname == 'treeExpanded');
    if (expanded) {
       collapseRemoteCommentReply(comment_index);
    } else {
       expandRemoteCommentReply(comment_index);
 }
}

function connectRemoteCommentReply(comment_index) {
    YUI().use('event', function(Y) {
        var toggleFunc = function() {
            toggleRemoteCommentReply(comment_index);
            return false;
        };

        var prefix = 'remote_comment_reply_expand_link_';

        Y.on('load', function(e) {
            $(prefix + comment_index).onclick = toggleFunc;
        }, window);
    });
}

function switchDisplay(tag_id1, tag_id2) {
    var tag1 = getElement(tag_id1);
    var tag2 = getElement(tag_id2);
    var display = tag1.style.display;
    tag1.style.display = tag2.style.display;
    tag2.style.display = display;
    return false;
}

