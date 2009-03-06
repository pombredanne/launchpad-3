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
}, '0.1', {requires:['cookie']});


// Lint-safe scripting URL.
var VOID_URL = '_:void(0);'.replace('_', 'javascript');


function registerLaunchpadFunction(func) {
    // registers a function to fire onload.
    // Use this for initilaizing any javascript that should fire once the page
    // has been loaded.
    connect(window, 'onload', func);
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
registerLaunchpadFunction(activateCollapsibles);

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
registerLaunchpadFunction(activateFoldables);

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
registerLaunchpadFunction(activateConstrainBugExpiration);

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
    function toggleFunc() {
        toggleRemoteCommentReply(comment_index);
        return false;
    }

    var prefix = 'remote_comment_reply_expand_link_';
    function func() {
        $(prefix + comment_index).onclick = toggleFunc;
    }

    registerLaunchpadFunction(func);
}

function switchDisplay(tag_id1, tag_id2) {
    var tag1 = getElement(tag_id1);
    var tag2 = getElement(tag_id2);
    var display = tag1.style.display;
    tag1.style.display = tag2.style.display;
    tag2.style.display = display;
    return false;
}

