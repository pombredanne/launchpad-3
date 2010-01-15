/* Copyright 2009 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Library for code review javascript.
 *
 * @module CodeReview
 * @requires base, lazr.anim, lazr.formoverlay
 */

YUI.add('code.codereview', function(Y) {

Y.codereview = Y.namespace('code.codereview');

var reviewer_picker; // The "Request a review" overlay
var lp_client;

var window_scroll_anim = new Y.Anim({
        node: 'window',
        duration: 1,
        easing: Y.Easing.easeOut
    });

/*
 * Connect all the links to their given actions.
 */
Y.codereview.connect_links = function() {

    var link = Y.one('#request-review');
    if (link !== null) {
        link.addClass('js-action');
        link.on('click', show_request_review_form);
    }
    link = Y.one('.menu-link-set_commit_message');
    if (link !== null) {
        link.addClass('js-action');
        link.on('click', edit_commit_message);
    }
    var widget = Y.lp.widgets['edit-commit-message'];
    widget.editor.on('save', function() {
            commit_message_listener(this.get('value'), true);
        });
    widget.editor.on('cancel', function() {
            commit_message_listener(this.get('value'), false);
        });

    link_scroller('#proposal-summary a.diff-link', '#review-diff');
    link_scroller('.menu-link-add_comment', '#add-comment', function() {
            Y.one('#add-comment-form textarea').focus();
        });
};


function link_scroller(link_selector, node_selector, on_end) {
    var link = Y.one(link_selector);
    if (!link) return;

    link.addClass('js-action');
    link.on('click', function(e) {
        e.halt();
        // Stop any running scrolling.
        window_scroll_anim.stop();
        // Detach any on end handlers.
        window_scroll_anim.detach('anim:end');
        var node = Y.one(node_selector);
        window_scroll_anim.set('to', {scroll: [0, node.getY() - 5] });
        if (on_end) {
            Y.log('on end set');
            window_scroll_anim.on('end', on_end);
        }
        window_scroll_anim.run();
    });
}

/*
 * Hide the commit message editor if the value is empty.
 *
 * If the commit message is empty, we want to show the
 * 'Set commit message' link again.  For consistency with
 * page updates we want to flash this link so the user can
 * see what we are doing.  If the commit message was saved
 * and is empty, then we flash green as all is good.  If the
 * user has cancelled the edit, and the commit message is
 * empty, then we flash the link red.
 */
function commit_message_listener(message, saved)
{
    if (message == '') {
        // Hide the multiline editor
        Y.one('#edit-commit-message').addClass('unseen');
        // Show the link again
        var link = Y.one('.menu-link-set_commit_message');
        link.removeClass('unseen');
        if (saved) {
            // Flash green.
            Y.lazr.anim.green_flash({node:link}).run();
        }
        else {
            // Flash red.
            Y.lazr.anim.red_flash({node:link}).run();
        }
    }
}

/*
 * Edit the commit message.
 *
 * Hide the link, show the multi-line editor, and set it to edit.
 */
function edit_commit_message(e) {
    // We are handling this click event.
    e.halt();
    // Make the edit button unseen.
    Y.one('#edit-commit-message').removeClass('unseen');
    // Remove the unseen class from the commit message.
    Y.one('.menu-link-set_commit_message').addClass('unseen');
    // Trigger the edit on the multiline editor.
    Y.lp.widgets['edit-commit-message']._triggerEdit(e);
}

/*
 * Show the "Request a reviewer" overlay.
 */
function show_request_review_form(e) {

    e.preventDefault();
    var config = {
        header: 'Request a review',
        step_title: 'Search'
    };

    reviewer_picker = Y.lp.picker.create(
        'ValidPersonOrTeam',
        function(result) {
            var review_type = Y.one("[id=field.review_type]").get('value');
            request_reviewer(result, review_type);
        },
        config);
    reviewer_picker.set('footer_slot', Y.Node.create([
        '<div>',
        '<div style="float: left; padding-right: 9px;">',
        '<label for="field.review_type">Review type:</label><br />',
        '<span class="fieldRequired">(Optional)</span>',
        '</div>',
        '<input class="textType" id="field.review_type" ',
        'name="field.review_type" size="14" type="text" value=""  /></div>'
        ].join(' ')));

    reviewer_picker.show();
}

/*
 * Actually perform the reviewer request.
 */
function request_reviewer(person, reviewtype) {

    // Add the temp "Requesting review..." text
    var table_row = Y.Node.create([
        '<tr><td colspan="4">',
        '<img src="/@@/spinner" />',
        'Requesting review...',
        '</td></tr>'].join(""));
    var last_element = Y.one('#email-review');
    var reviewer_table = last_element.get('parentNode');
    reviewer_table.insertBefore(table_row, last_element);


    var context = LP.client.cache.context;
    if (lp_client === undefined) {
        lp_client = new LP.client.Launchpad();
    }

    var config = {
        parameters: {
            reviewer: LP.client.get_absolute_uri(person.api_uri),
            review_type: reviewtype
        },
        on: {
            success: function() {
                var username = person.api_uri.substr(
                    2, person.api_uri.length);
                add_reviewer_html(username);
            },
            failure: function(result) {
                // XXX: rockstar - The error handling story in LP is close to
                // non-existent.  Fix that, then fix this.
                alert('An error has occurred. Unable to request review.');
                Y.log(result);
            }
        }
    };
    lp_client.named_post(context.self_link,
        'nominateReviewer', config);
}


/*
 * Update the reviewers table.
 */
function add_reviewer_html(username) {

    var VOTES_TABLE_PATH = '+votes';
    Y.io(VOTES_TABLE_PATH, {
        on: {
            success: function(id, response) {
                var target = Y.one('#votes-target');
                target.set('innerHTML', response.responseText);

                Y.codereview.connect_links();
                var new_reviewer = Y.one('#review-' + username);
                var anim = Y.lazr.anim.green_flash({node: new_reviewer});
                anim.run();
            },
            failure: function() {}
        }
    });
}


var NumberToggle = function () {
        NumberToggle.superclass.constructor.apply(this, arguments);
};


var update_nos = function(){
    var new_display = 'none';
    if (this.get('checked')) {
        new_display = 'block';
    }
    Y.all('td.line-no').setStyle('display', new_display);
};


NumberToggle.NAME = 'numbertoggle';

NumberToggle.ATTRS = {
};
Y.extend(NumberToggle, Y.Widget, {
    renderUI: function() {
        var ui = Y.Node.create('<li><label>' +
            '<input type="checkbox" checked="checked" id="show-no"/>' +
            '&nbsp;Show line numbers</label></li>');
        var ul = Y.one('#review-diff div div ul.horizontal');
        if (ul) {
            ul.appendChild(ui);
        }
    },
    bindUI: function() {
        var cb = Y.one('#show-no');
        if (cb) {
            cb.on('click', update_nos);
        }
    }
});

Y.codereview.NumberToggle = NumberToggle;

}, "0.1", {"requires": ["base", "widget", "lazr.anim", "lazr.formoverlay", "lp.picker"]});
