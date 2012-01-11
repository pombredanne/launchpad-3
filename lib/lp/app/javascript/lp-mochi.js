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
