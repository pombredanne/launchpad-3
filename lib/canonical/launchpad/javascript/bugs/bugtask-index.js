/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Handling of form overlay widgets for bug pages.
 *
 * @module BugtaskIndex
 * @requires base, node, lazr.formoverlay, lazr.anim
 */

YUI.add('bugs.bugtask_index', function(Y) {

var bugs = Y.namespace('bugs');

/*
 * The lazr.FormOverlay object.
 */
var duplicate_form_overlay;
var privacy_form_overlay;

/*
 * The url of the page used to update bug duplicates.
 */
var update_dupe_url;

/*
 * The launchpad js client that will be used to update the duplicate.
 */
var lp_client;

/*
 * The launchpad client entry for the current bug.
 */
var lp_bug_entry;
var form_load_callbacks = {};
var submit_button_html =
    '<button type="submit" name="field.actions.change" ' +
    'value="Change" class="lazr-pos lazr-btn" >OK</button>';
var cancel_button_html =
    '<button type="button" name="field.actions.cancel" ' +
    'class="lazr-neg lazr-btn" >Cancel</button>';
var privacy_link;
var privacy_spinner;


Y.bugs.setup_bugtask_index = function() {
    /*
     * Check the page for links related to overlay forms and request the HTML
     * for these forms.
     */
    Y.on('domready', function() {
        // If the user is not logged in, then we need to defer to the
        // default behaviour.
        if (LP.client.links.me === undefined){
            return;
        }

        Y.on('io:complete', function(id, response_object) {
            form_load_callbacks[id](response_object.responseText);
        }, this);

        // First look for 'Mark as duplicate' links.
        var update_dupe_links = Y.all('.menu-link-mark-dupe');

        // If there are none, check for any 'change duplicate bug' links.
        if (!update_dupe_links){
            update_dupe_links = Y.all('#change_duplicate_bug');
        }

        if (update_dupe_links) {
            // First things first, pre-load the mark-dupe form.
            update_dupe_url = update_dupe_links.item(0).getAttribute('href');
            var mark_dupe_form_url = update_dupe_url + '/++form++';
            var dupe_form_id = Y.io(mark_dupe_form_url);
            form_load_callbacks[dupe_form_id.id] = createBugDuplicateFormOverlay;

            // Add an on-click handler to any links found that displays
            // the form overlay.
            update_dupe_links.on('click', function(e){
                // Only go ahead if we have received the form content by the
                // time the user clicks:
                if (duplicate_form_overlay){
                    e.preventDefault();
                    duplicate_form_overlay.show();
                }
            });
            // Add a class denoting them as js-action links.
            update_dupe_links.addClass('js-action');
        }

        privacy_link = Y.get('#privacy-link');

        if (privacy_link) {
            var privacy_link_url = privacy_link.getAttribute('href') + '/++form++';
            var privacy_div = Y.get('#privacy-text');
            var privacy_html = privacy_link.get('innerHTML') + ' ';
            privacy_div.set('innerHTML', privacy_html);
            var privacy_text = Y.get('#privacy-text');
            privacy_link = Y.Node.create(
                '<a href="' + privacy_link_url + '" id="privacy-link">' +
                '<img src="/@@/edit"></a>');
            privacy_text.appendChild(privacy_link);
            privacy_spinner = Y.Node.create(
                '<img src="/@@/spinner" style="display: none" />');
            privacy_text.appendChild(privacy_spinner);
            var privacy_form_id = Y.io(privacy_link_url);
            form_load_callbacks[privacy_form_id.id] = create_privacy_form_overlay;

            privacy_link.on('click', function(e) {
                if (privacy_form_overlay) {
                    e.preventDefault();
                    privacy_form_overlay.show();
                    // XXX Abel Deuring 2009-04-23, bug 365462
                    // Y.get('#field.private') returns null.
                    // Seems that YUI does not like IDs containing a '.'
                    document.getElementById('field.private').focus();
                }
            });
            privacy_link.addClass('js-action');
        }
    });
};

/*
 * Creates the duplicate form overlay using the passed form content.
 */
function createBugDuplicateFormOverlay(form_content) {
    duplicate_form_overlay = new Y.lazr.FormOverlay({
        headerContent: '<h2>Mark bug report as duplicate</h2>',
        form_content: 'Marking the bug as a duplicate will, by default, ' +
                      'hide it from search results listings.' + form_content,
        form_submit_button: Y.Node.create(submit_button_html),
        form_cancel_button: Y.Node.create(cancel_button_html),
        centered: true,
        form_submit_callback: update_bug_duplicate,
        visible: false
    });
    duplicate_form_overlay.render('#duplicate-form-container');
}

/*
 * Update the bug duplicate via the LP API
 */
function update_bug_duplicate(data) {
    // Hide the formoverlay:
    duplicate_form_overlay.hide();

    // Add the spinner...
    var dupe_span = Y.get('#mark-duplicate-text');
    dupe_span.addClass('update-in-progress-message');

    // Create the lp client and bug entry if we haven't done so already.
    if (lp_client === undefined) {
        lp_client = new LP.client.Launchpad();
    }

    if (lp_bug_entry === undefined) {
        var bug_repr = LP.client.cache.bug;
        lp_bug_entry = new LP.client.Entry(
            lp_client, bug_repr, bug_repr.self_link);
    }

    // Set the new duplicate link on the bug entry.
    var new_dup_url = null;
    var new_dup_id = data['field.duplicateof'];
    // "make lint" claims the expession operator below should be "!--".
    // If we use this operator, we cannot unset the duplicate number.
    if (new_dup_id != '') {
        var self_link = lp_bug_entry.get('self_link');
        var last_slash_index = self_link.lastIndexOf('/');
        new_dup_url = self_link.slice(0, last_slash_index+1) + new_dup_id;
    }
    var old_dup_url = lp_bug_entry.get('duplicate_of_link');
    lp_bug_entry.set('duplicate_of_link', new_dup_url);

    // Create a config for the lp_save method
    config = {
        on: {
            success: function(updated_entry) {
                dupe_span.removeClass('update-in-progress-message');
                lp_bug_entry = updated_entry;

                // XXX noodles 2009-03-17 bug=336866 It seems the etag
                // returned by lp_save() is incorrect. Remove it for now
                // so that the second save does not result in a '412
                // precondition failed' error.
                lp_bug_entry.removeAtt('http_etag');

                if (new_dup_url !== null) {
                    dupe_span.set('innerHTML', [
                        'Duplicate of <a href="/bugs/' + new_dup_id + '">',
                        'bug #' + new_dup_id +'</a> ',
                        '<a class="menu-link-mark-dupe js-action" ',
                        'href="' + update_dupe_url + '">',
                        '<img src="/@@/edit" /></a>'
                        ].join(''));
                } else {
                    dupe_span.set('innerHTML',
                        '<a class="menu-link-mark-dupe js-action" href="' +
                        update_dupe_url + '">' +
                        '<img src="/@@/bug-dupe-icon" /> ' +
                        'Mark as duplicate</a>');
                }
                Y.lazr.anim.green_flash({node: dupe_span}).run();
                // ensure the new link is hooked up correctly:
                dupe_span.query('a.menu-link-mark-dupe').on(
                    'click', function(e){
                        e.preventDefault();
                        duplicate_form_overlay.show();
                    });
            },
            failure: function(id, request) {
                dupe_span.removeClass('update-in-progress-message');
                if (request.status == 400) {
                    duplicate_form_overlay.showError(
                        new_dup_id + ' is not a valid bug number or' +
                        ' nickname.');
                } else {
                    duplicate_form_overlay.showError(request.responseText);
                }
                duplicate_form_overlay.show();

                // Reset the lp_bug_entry.duplicate_of_link as it wasn't
                // updated.
                lp_bug_entry.set('duplicate_of_link', old_dup_url);

            }
        }
    };

    // And save the updated entry.
    lp_bug_entry.lp_save(config);
}

/*
 * Create the privacy settings form overlay.
 *
 * @method create_privacy_form_overlay
 * @param form_content {string} The HTML data of the form overlay.
 */
var create_privacy_form_overlay = function(form_content) {
    privacy_form_overlay = new Y.lazr.FormOverlay({
        headerContent: '<h2>Change privacy settings</h2>',
        form_content: form_content,
        form_submit_button: Y.Node.create(submit_button_html),
        form_cancel_button: Y.Node.create(cancel_button_html),
        centered: true,
        form_submit_callback: update_privacy_settings,
        visible: false
    });
    privacy_form_overlay.render('#privacy-form-container');
    var node = Y.get('#form-container');
};

var update_privacy_settings = function(data) {
    privacy_form_overlay.hide();

    var privacy_text = Y.get('#privacy-text');
    privacy_link.setStyle('display', 'none');
    privacy_spinner.setStyle('display', 'inline');

    if (lp_client === undefined) {
        lp_client = new LP.client.Launchpad();
    }

    if (lp_bug_entry === undefined) {
        var bug_repr = LP.client.cache.bug;
        lp_bug_entry = new LP.client.Entry(
            lp_client, bug_repr, bug_repr.self_link);
    }

    var private = data['field.private'] !== undefined;
    var security_related =
        data['field.security_related'] !== undefined;

    lp_bug_entry.set('private', private);
    lp_bug_entry.set('security_related', security_related);

    var config = {
        on: {
            success: function (updated_entry) {
                var privacy_text = Y.get('#privacy-text');
                privacy_spinner.setStyle('display', 'none');
                privacy_link.setStyle('display', 'inline');
                lp_bug_entry = updated_entry;

                // XXX noodles 2009-03-17 bug=336866 It seems the etag
                // returned by lp_save() is incorrect. Remove it for now
                // so that the second save does not result in a '412
                // precondition failed' error.
                lp_bug_entry.removeAtt('http_etag');

                var privacy_div = Y.get('#privacy');
                if (private) {
                    privacy_div.removeClass('public');
                    privacy_div.addClass('private');
                    privacy_text.set(
                        'innerHTML',
                        'This report is <strong>private</strong> ');
                } else {
                    privacy_div.removeClass('private');
                    privacy_div.addClass('public');
                    privacy_text.set(
                        'innerHTML', 'This report is public ');
                }
                privacy_text.appendChild(privacy_link);
                privacy_text.appendChild(privacy_spinner);

                var security_message = Y.get('#security-message');
                if (security_related) {
                    if (security_message === null) {
                        var security_message_html = [
                            '<div style="',
                            '    margin-top: 0.5em;',
                            '    padding-right: 18px;',
                            '    background:url(/@@/security)',
                            '    center right no-repeat;"',
                            '    id="security-message"',
                            '>Security vulnerability</div>'
                        ].join('');
                        security_message = Y.Node.create(security_message_html);
                        privacy_div.appendChild(security_message);
                    }
                } else {
                    if (security_message !== null) {
                        privacy_div.removeChild(security_message);
                    }
                }
                Y.lazr.anim.green_flash({node: privacy_div}).run();
            },
            failure: function(id, request) {
                privacy_spinner.setStyle('display', 'none');
                privacy_link.setStyle('display', 'inline');
                Y.lazr.anim.red_flash({node: privacy_div}).run();
                privacy_form_overlay.showError(request.responseText);
                privacy_form_overlay.show();
            }
        }
    };
    lp_bug_entry.lp_save(config);
};

}, '0.1', {requires: ['base', 'oop', 'node', 'event', 'io-base',
                      'lazr.formoverlay', 'lazr.anim']});
