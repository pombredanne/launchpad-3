// Some Javascript code from Plone Solutions
// http://www.plonesolutions.com, thanks!

function initHelpPanel() {
  /* 
    With CSS but no JavaScript, Launchpad is useful with the help always off,
    but not with the help always on, because it covers the page content.
    So the help panel is hidden by default. Then if JavaScript is available,
    this function hooks up the expand/collapse JavaScript to the panel, then
    reveals it in collapsed mode.
  */
  if (document.getElementById) {
    tab = document.getElementById('help-tab');
    helpwidget = document.getElementById('help');
    tab.onclick = function() {
      if (helpwidget.className == 'closed') {
        helpwidget.className = 'open'
      } else {
        helpwidget.className = 'closed'
      };
      return false;
    }
    helpwidget.style.visibility = 'visible';
  }
}

var PortletManager = {
    cookie_scope: '',
    expanded_portlets: [],

    readCookie: function() {
        // extract the expanded_portlets cookie
        // Code adapted from http://trac.mochikit.com/ticket/167
        var cookies = document.cookie;
        var prefix = 'expanded_portlets=';
        var begin = cookies.indexOf('; ' + prefix);
        if (begin == -1) {
            begin = cookies.indexOf(prefix);
            if (begin != 0) {
                // No cookie
                this.expanded_portlets = [];
                return;
            }
        } else {
            begin += 2;
        }
        var end = cookies.indexOf(';', begin);
        if (end == -1) {
            end = cookies.length;
        }
        var value = unescape(cookies.substring(begin + prefix.length, end));
        if (value) {
            this.expanded_portlets = value.split(',');
        } else {
            this.expanded_portlets = [];
        }
    },

    writeCookie: function() {
        var value = escape(this.expanded_portlets.join(','));
        var expire = new Date();
        // Keep the cookie for 31 days
        expire.setTime(expire.getTime() + 31 * 24 * 3600 * 1000);
        document.cookie = ('expanded_portlets=' + value + '; Expires=' +
            expire.toGMTString() + this.cookie_scope);
    },

    shouldBeExpanded: function(portlet_id) {
        return findValue(this.expanded_portlets, portlet_id) >= 0;
    },

    togglePortlet: function(ev) {
        var portlet = getFirstParentByTagAndClassName(
            ev.src(), 'div', 'portlet');
        var is_expanded = hasElementClass(portlet, 'expanded');
        if (is_expanded) {
            swapElementClass(portlet, 'expanded', 'collapsed');
        } else {
            swapElementClass(portlet, 'collapsed', 'expanded');
        }
        is_expanded = !is_expanded;

        var portlet_id = getNodeAttribute(portlet, 'id');
        if (!portlet_id) {
            return;
        }
        var pos = findValue(this.expanded_portlets, portlet_id);
        if (is_expanded && pos < 0) {
            this.expanded_portlets.push(portlet_id);
            this.writeCookie()
        } else if (!is_expanded && pos >= 0) {
            this.expanded_portlets.splice(pos, 1);
            this.writeCookie()
        }
    },

    initialize: function(cookie_scope) {
        this.cookie_scope = cookie_scope;
        this.readCookie();
        var portlets_container = getElement('portlets');
        if (!portlets_container) {
            return;
        }
        var portlets = getElementsByTagAndClassName(
            'div', 'portlet', portlets_container);
        for (var i = 0; i < portlets.length; i++) {
            var portlet = portlets[i];
            var portlet_id = getNodeAttribute(portlet, 'id');
            var headings = getElementsByTagAndClassName('h2', null, portlet);
            // All portlets should have a heading, but check anyway to
            // avoid problems.
            if (portlet_id == 'actions' || headings.length == 0) {
                continue;
            }

            if (portlet_id && this.shouldBeExpanded(portlet_id)) {
                portlet.className = 'portlet expanded';
            } else {
                portlet.className = 'portlet collapsed';
            }
            var heading = headings[0];

            // Create an anchor to handle click-events, and reparent the
            // heading's children into it.  We do this rather than
            // connecting the event handler to the heading so that it
            // can be toggled with the keyboard.
            var anchor = document.createElement('a');
            anchor.href = 'javascript:undefined';
            while (heading.hasChildNodes()) {
                var child = heading.firstChild;
                heading.removeChild(child);
                anchor.appendChild(child);
            }
            heading.appendChild(anchor);

            connect(anchor, 'onclick', this, 'togglePortlet');
        }
    }
}

function registerLaunchpadFunction(func) {
    // registers a function to fire onload.
    // Use this for initilaizing any javascript that should fire once the page
    // has been loaded.
    connect(window, 'onload', func);
}

function sendWindowDims() {
    dims = getViewportDimensions();
    doSimpleXMLHttpRequest('/+dims', dims);
}
registerLaunchpadFunction(sendWindowDims);

function getContentArea() {
    // to end all doubt on where the content sits. It also felt a bit
    // silly doing this over and over in every function, even if it is
    // a tiny operation. Just guarding against someone changing the
    // names again, in the name of semantics or something.... ;)
    var node = document.getElementById('maincontent');
    if (!node) {
        node = document.getElementById('content');
    }
    return node;
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
    if (!document.getElementsByTagName)
        return false;
    if (!document.getElementById)
        return false;

    // only search in the content-area
    var contentarea = getContentArea();
    if (!contentarea)
        return false;

    // gather all objects that are to be collapsed
    // we only do fieldsets for now. perhaps DIVs later...
    var collapsibles = contentarea.getElementsByTagName('fieldset');

    for (var i = 0; i < collapsibles.length; i++) {
        if (collapsibles[i].className.indexOf('collapsible') == -1)
            continue;

        var legends = collapsibles[i].getElementsByTagName('LEGEND');

        // get the legend
        // if there is no legend, we do not touch the fieldset at all.
        // we assume that if there is a legend, there is only
        // one. nothing else makes any sense
        if (!legends.length)
            continue;
        var legend = legends[0];

        //create an anchor to handle click-events
        var anchor = document.createElement('a');
        anchor.href = '#';
        anchor.onclick = toggleCollapsible;

        // add the icon/button with its functionality to the legend
        var icon = document.createElement('img');
        icon.setAttribute('src','/@@/treeExpanded');
        icon.setAttribute('class','collapseIcon');
        icon.setAttribute('height','16');
        icon.setAttribute('width','16');

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

function toggleCollapsible(e) {
    // this is the function that collapses/expands fieldsets. 

    // "this" is the node that the event is attached to
    var node = this;

    // walk up the node hierarchy until we find the <legend> element
    while (node.nodeName.toLowerCase() != 'legend') {
        node = node.parentNode;
        if (!node)
            return false;
    }

    // the expander image is legend -> a -> img
    var icon = node.firstChild.firstChild;
    var legend = node;

    if (icon.getAttribute('src').indexOf('/@@/treeCollapsed') != -1) {
        // that was an ugly check, but IE rewrites image sources to
        // absolute urls from some sick reason....
        icon.setAttribute('src','/@@/treeExpanded');
        swapElementClass(legend.parentNode.lastChild, 'collapsed', 'expanded');
        swapElementClass(
            legend.parentNode.childNodes[1], 'expanded', 'collapsed');
    } else {
        icon.setAttribute('src','/@@/treeCollapsed');
        swapElementClass(legend.parentNode.lastChild, 'expanded', 'collapsed');
        swapElementClass(
            legend.parentNode.childNodes[1], 'collapsed', 'expanded');
    }
    return false;
}

function activateFoldables() {
    // Create links to toggle the display of foldable content.
    var maincontent = document.getElementById('maincontent');
    if (!maincontent) {
        return;
    }

    var included = getElementsByTagAndClassName(
        'span', 'foldable', maincontent);
    var quoted = getElementsByTagAndClassName(
        'span', 'foldable-quoted', maincontent);
    var elements = concat(included, quoted)
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
        ellipsis.href = 'javascript:void(0)';
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

function toggleFoldable(e) {
    // Collapse/expand a folded passage of text or a signature. 
    var node = this;
    while (node = node.nextSibling) {
        if (node.nodeType != 1 && node.className.indexOf('foldable') == -1) {
            // node is not an ELEMENT_NODE of foldable class
            continue;
        }
        if (node.style.display == 'none') {
            node.style.display = 'inline';
        } else {
            node.style.display = 'none';
        }
    }
}

function toggleExpandableTableRow(element_id) {
      row = document.getElementById(element_id)
      view_icon = document.getElementById(element_id + "-arrow")
      if (row.style.display == "table-row") {
        row.style.display = "none";
        view_icon.setAttribute("src", "/@@/treeCollapsed")
      } else {
        row.style.display = "table-row";
        view_icon.setAttribute("src", "/@@/treeExpanded")
      }
      return false;
}

function toggleExpandableTableRows(class_name) {
      view_icon = document.getElementById(class_name + "-arrow");
      all_page_tags = document.getElementsByTagName("*");
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

// Add/remove items between selection lists by double clicking:
function addSelectedKeywords(fromlist,tolist) {
    var predefSubjects = document.getElementById(fromlist);
    for (var x = 0; x < predefSubjects.length; x++) {
        if (predefSubjects[x].selected) {
            addNewKeyword(tolist, predefSubjects[x].text);
        }
    }
}

function addNewKeyword(tolist, newWord) {
    var selSubjects = document.getElementById(tolist);
    for (var x = 0; x < selSubjects.length; x++) {
        if (selSubjects[x].text == newWord) {
            return false;
        }
    }
    var ssl = selSubjects.length;
    selSubjects[ssl] = new Option(newWord);
}

function selectAllWords() {
    var keyword = document.getElementsByTagName('select');

    for (var i = 0; i < keyword.length; i++) {
        if (keyword[i].multiple) {
            for (var x = 0; x < keyword[i].options.length; x++) {
                keyword[i].options[x].selected = true;
            }
        }
    }
}

function removeWords(thelist) {
    var selSubjects = document.getElementById(thelist);

    for (var x = selSubjects.length-1; x >= 0 ; x--) {
        if (selSubjects[x].selected) {
            selSubjects[x] = null;
        }
    }
}

// XXX: jamesh 2006-08-09
// The setFocus() function should be removed once we've migrated away
// from GeneralForm.

// Focus on error or tabindex=1 
function setFocus() {
    var xre = new RegExp(/\berror\b/);
    var formnodes, formnode, divnodes, node, inputnodes, inputnode;

    // Search only forms to avoid spending time on regular text
    formnodes = document.getElementsByTagName('form');
    for (var f = 0; (formnode = formnodes.item(f)); f++) {
        // Search for errors first, focus on first error if found
        divnodes = formnode.getElementsByTagName('div');
        for (var i = 0; (node = divnodes.item(i)); i++) {
            if (xre.exec(node.className)) {
                inputnode = node.getElementsByTagName('input').item(0);
                if (inputnode) {
                    inputnode.focus();
                    return;   
                }
            }
        }

        // If no error, focus on input element with tabindex 1
        var inputnodes = formnode.getElementsByTagName('input');
        for (var i = 0; (node = inputnodes.item(i)); i++) {
           if (node.getAttribute('tabindex') == 1) {
               node.focus();
               return;
           }
        }
    }
}
registerLaunchpadFunction(setFocus);

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
    if (!iframe.src) {
        // The first time this handler runs the window may not have been
        // set up yet; sort that out.
        iframe.style.width = width + 'px';
        iframe.style.height = height + 'px';
        iframe.style.position = 'absolute';
        iframe.style.background = 'white';
        iframe.src = url
    }
    iframe.style.display = 'inline';
    // I haven't found a way of making the search form focus again when
    // the popup window is redisplayed. I tried doing an
    //    iframe.contentDocument.searchform.search.focus()
    // but nothing happens.. -- kiko, 2007-03-12
}

// from richard braine for the source import forms
function morf(x) {
    // morf morphs form. it takes a radio choice as argument
    // and shows and hides given divs as a result
    function showdiv() {
        for(var i = 0; i < arguments.length; i++) {
            //document.all[arguments[i]].style.visibility='visible';
            document.getElementById(arguments[i]).style.visibility='visible';
        }
    }
    function hidediv(){
        for(var i = 0; i < arguments.length; i++) {
            //document.all[arguments[i]].style.visibility='hidden';
            document.getElementById(arguments[i]).style.visibility='hidden';
        }
    }
    switch(true){
    case x=='cvs':
        showdiv('cvsdetails');
        hidediv('svndetails');
        break;
    case x=='svn':
        showdiv('svndetails');
        hidediv('cvsdetails');
        break;
    // case x=='arch':
    //     showdiv('archdetails');
    //     hidediv('cvsdetails', 'svndetails');
    //     break;
    }
}

function selectWidget(widget_name, event) {
  if (event && (event.keyCode == 9 || event.keyCode == 13))
      // Avoid firing if user is tabbing through or simply pressing
      // enter to submit the form.
      return;
  document.getElementById(widget_name).checked = true;
}

// Set the disabled attribute of the widgets with the given ids.
function setDisabled(disabled /* widget_ids ... */) {
    for (var i=1; i<arguments.length; i++) {
        var widget = document.getElementById(arguments[i])
        widget.disabled = disabled
    }
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
    new_text_area.setAttribute('onKeyPress', getNodeAttribute(current_text_input, 'onkeypress'));
    new_text_area.setAttribute('onChange', getNodeAttribute(current_text_input, 'onchange'));
    new_text_area.value = current_text_input.value;
    swapDOM(current_text_input, new_text_area);

}

function upgradeToTextAreaForTranslation(text_input_id) {
    var rows = 6;

    current_text_input = getElement(text_input_id);
    current_text_input.parentNode.removeChild(
        getElement(text_input_id + '_to_textarea'));
    convertTextInputToTextArea(text_input_id, rows);
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

function writeTextIntoPluralTranslationFields(
    from_id, to_id_pattern, nplurals) {
    // skip when x is 0, as that is the singular
    for (var x = 1; x < nplurals; x++) {
        to_id = to_id_pattern + x + "_new";
        copyInnerHTMLById(from_id, to_id);
    }
}

function switchBugBranchFormAndWhiteboard(id) {
    var div = document.getElementById('bugbranch' + id);
    var wb = document.getElementById('bugbranch' + id + '-wb');

    if (div.style.display == "none") {
        /* Expanding the form */
        if (wb != null) {
            wb.style.display = "none";
        }
        div.style.display = "block";
        /* Use two focus calls to get the browser to scroll to the end of the
         * form first, then focus back to the first field of the form.
         */
        document.getElementById('field'+id+'.actions.update').focus();
        document.getElementById('field'+id+'.status').focus();
    } else {
        if (wb != null) {
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
        if (wb != null) {
            wb.style.display = "none";
        }
        div.style.display = "block";
        /* Use two focus calls to get the browser to scroll to the end of the
         * form first, then focus back to the first field of the form.
         */
        document.getElementById('field' + id + '.actions.change').focus();
        document.getElementById('field' + id + '.summary').focus();
    } else {
        if (wb != null) {
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
    }
    inputs = document.getElementsByTagName('input');
    for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].name == 'field.bugtracker'
            || inputs[i].name == 'field.official_malone') {
            inputs[i].onclick = constraint;
        }
    }
}
registerLaunchpadFunction(activateConstrainBugExpiration);

function updateField(field, enabled)
{
    field.disabled = !enabled;
    field.style.backgroundColor = enabled ? 'white' : 'lightgrey';
}


function collapseRemoteCommentReply(comment_index) {
   $('remote_comment_reply_tree_icon_' + comment_index).src = '/@@/treeCollapsed';
   $('remote_comment_reply_div_' + comment_index).style.display = 'none';
}

function expandRemoteCommentReply(comment_index) {
   $('remote_comment_reply_tree_icon_' + comment_index).src = '/@@/treeExpanded';
   $('remote_comment_reply_div_' + comment_index).style.display = 'block';
}

function toggleRemoteCommentReply(comment_index) {
   var imgname = $('remote_comment_reply_tree_icon_' + comment_index).src.split('/').pop();
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

    function func() {
        $('remote_comment_reply_expand_link_' + comment_index).onclick = toggleFunc;
    }

    registerLaunchpadFunction(func);
}
