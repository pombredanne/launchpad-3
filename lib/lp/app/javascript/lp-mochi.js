// Copyright 2010 Canonical Ltd.  All rights reserved.
//
// Launchpad JavaScript core functions that require the MochiKit library.

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
        var to_select = to_id_pattern + x + "_new_select";
        copyInnerHTMLById(from_id, to_id);
        document.getElementById(to_select).checked = true;
    }
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
    LPS.use('event', function(Y) {
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

function unescapeHTML(unescaped_string) {
    // Based on prototype's unescapeHTML method.
    // See launchpad bug #78788 for details.
    var div = document.createElement('div');
    div.innerHTML = unescaped_string;
    return div.childNodes[0] ? div.childNodes[0].nodeValue : '';
}

