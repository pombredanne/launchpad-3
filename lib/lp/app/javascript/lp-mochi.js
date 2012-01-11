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
