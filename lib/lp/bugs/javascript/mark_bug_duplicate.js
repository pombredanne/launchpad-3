/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Provide functionality for marking a bug as a duplicate.
 *
 * @module bugs
 * @submodule mark_bug_duplicate
 */
YUI.add('lp.bugs.mark_bug_duplicate', function(Y) {

var namespace = Y.namespace('lp.bugs.mark_bug_duplicate');

// Overlay related vars.
var submit_button_html =
    '<button type="submit" name="field.actions.change" ' +
    'value="Change" class="lazr-pos lazr-btn" >OK</button>';
var cancel_button_html =
    '<button type="button" name="field.actions.cancel" ' +
    'class="lazr-neg lazr-btn" >Cancel</button>';

/**
 * Manage the process of marking a bug as a duplicate.
 * This widget does no rendering itself; it is used to enhance existing HTML.
 */
namespace.MarkBugDuplicate = Y.Base.create("markBugDupeWidget", Y.Widget, [], {
    initializer: function(cfg) {
        var update_dupe_link = cfg.update_dupe_link;
        if (update_dupe_link) {
            // First things first, pre-load the mark-dupe form.
            var mark_dupe_form_url =
                update_dupe_link.get('href') + '/++form++';

            var form_header = '<p>Marking this bug as a duplicate will,' +
                              ' by default, hide it from search results ' +
                              'listings.</p>';

            var duplicates_div = this.get('duplicates_div');
            if (Y.Lang.isValue(duplicates_div)) {
                form_header = form_header +
                    '<p class="block-sprite large-warning">' +
                    '<strong>Note:</strong> ' +
                    'This bug has duplicates of its own. ' +
                    'If you go ahead, they too will become duplicates of ' +
                    'the bug you specify here.  This cannot be undone.' +
                    '</p>';
            }

            this.duplicate_form_overlay = new Y.lazr.FormOverlay({
                headerContent: '<h2>Mark bug report as duplicate</h2>',
                form_header: form_header,
                form_submit_button: Y.Node.create(submit_button_html),
                form_cancel_button: Y.Node.create(cancel_button_html),
                centered: true,
                form_submit_callback:
                    Y.bind(this.update_bug_duplicate, this),
                visible: false,
                io_provider: cfg.io_provider
            });
            this.duplicate_form_overlay.render('#duplicate-form-container');
            this.duplicate_form_overlay.loadFormContentAndRender(
                mark_dupe_form_url);

            // Add an on-click handler to any links found that displays
            // the form overlay.
            var that = this;
            update_dupe_link.on('click', function(e) {
                // Only go ahead if we have received the form content by the
                // time the user clicks:
                if (that.duplicate_form_overlay){
                    e.preventDefault();
                    that.duplicate_form_overlay.show();
                    Y.DOM.byId('field.duplicateof').focus();
                }
            });
            // Add a class denoting them as js-action links.
            update_dupe_link.addClass('js-action');
        }
    },

    // Bug was successfully marked as a duplicate, update the UI.
    update_bug_duplicate_success: function(updated_entry, new_dup_url,
                                           new_dup_id) {
        updated_entry.set('duplicate_of_link', new_dup_url);
        this.set('lp_bug_entry', updated_entry);

        var dupe_span = this.get('dupe_span');
        var update_dup_url = dupe_span.one('a').get('href');
        if (Y.Lang.isValue(new_dup_url)) {
            dupe_span.setContent([
                '<a id="change_duplicate_bug" ',
                'title="Edit or remove linked duplicate bug" ',
                'class="sprite edit action-icon">Edit</a>',
                'Duplicate of <a>bug #</a>'].join(""));
            dupe_span.all('a').item(0) .set('href', update_dup_url);
            dupe_span.all('a').item(1)
                .set('href', '/bugs/' + new_dup_id)
                .appendChild(document.createTextNode(new_dup_id));
            var duplicates_div = this.get('duplicates_div');
            Y.log(duplicates_div)
            if (Y.Lang.isValue(duplicates_div)) {
                duplicates_div.remove(true);
            }
            this.show_comment_on_duplicate_warning();
        } else {
            dupe_span.addClass('sprite bug-dupe');
            dupe_span.setContent([
                '<a class="menu-link-mark-dupe js-action">',
                'Mark as duplicate</a>'].join(""));
            dupe_span.one('a').set('href', update_dup_url);
            this.hide_comment_on_duplicate_warning();
        }
        Y.lp.anim.green_flash({
            node: dupe_span,
            duration: this.get('anim_duration')
            }).run();
        // ensure the new link is hooked up correctly:
        var that = this;
        dupe_span.one('a').on(
            'click', function(e){
                e.preventDefault();
                that.duplicate_form_overlay.show();
                Y.DOM.byId('field.duplicateof').focus();
            });
    },

    // There was an error marking a bug as a duplicate.
    update_bug_duplicate_failure: function(response, old_dup_url, new_dup_id) {
        // Reset the lp_bug_entry.duplicate_of_link as it wasn't
        // updated.
        this.get('lp_bug_entry').set('duplicate_of_link', old_dup_url);
        if (response.status === 400) {
            this.duplicate_form_overlay.showError(
                new_dup_id + ' is not a valid bug number or nickname.');
        } else {
            this.duplicate_form_overlay.showError(response.responseText);
        }
        this.duplicate_form_overlay.show();
    },

    /**
     * Update the bug duplicate via the LP API
     */
    update_bug_duplicate: function(data) {
    // XXX noodles 2009-03-17 bug=336866 It seems the etag
    // returned by lp_save() is incorrect. Remove it for now
    // so that the second save does not result in a '412
    // precondition failed' error.
    //
    // XXX deryck 2009-04-29 bug=369293 Also, this has to
    // happen before *any* call to lp_save now that bug
    // subscribing can be done inline.  Named operations
    // don't return new objects, making the cached bug's
    // etag invalid as well.
    var lp_bug_entry = this.get('lp_bug_entry');
    lp_bug_entry.removeAttr('http_etag');

    // Hide the formoverlay:
    this.duplicate_form_overlay.hide();

    var new_dup_url = null;
    var new_dup_id = Y.Lang.trim(data['field.duplicateof'][0]);
    if (new_dup_id !== '') {
        var self_link = lp_bug_entry.get('self_link');
        var last_slash_index = self_link.lastIndexOf('/');
        new_dup_url = self_link.slice(0, last_slash_index+1) + new_dup_id;
    }
    var old_dup_url = lp_bug_entry.get('duplicate_of_link');
    lp_bug_entry.set('duplicate_of_link', new_dup_url);

    var dupe_span = this.get('dupe_span');
    var that = this;
    var config = {
        on: {
            start: function() {
                dupe_span.removeClass('sprite bug-dupe');
                dupe_span.addClass('update-in-progress-message');
            },
            end: function() {
                dupe_span.removeClass('update-in-progress-message');
            },
            success: function(updated_entry) {
                that.update_bug_duplicate_success(
                    updated_entry, new_dup_url, new_dup_id);
            },
            failure: function(id, response) {
                that.update_bug_duplicate_failure(
                    response, old_dup_url, new_dup_id);
            }
        }
    };
    // And save the updated entry.
    lp_bug_entry.lp_save(config);
    },

    /*
     * Ensure that a warning about adding a comment to a duplicate bug
     * is displayed.
     *
     * @method show_comment_on_duplicate_warning
     */
    show_comment_on_duplicate_warning: function() {
        var duplicate_warning = Y.one('#warning-comment-on-duplicate');
        if (duplicate_warning === null) {
            var container = Y.one('#add-comment-form');
            var first_node = container.get('firstChild');
            duplicate_warning = Y.Node.create(
                ['<div class="warning message"',
                 'id="warning-comment-on-duplicate">',
                 'Remember, this bug report is a duplicate. ',
                 'Comment here only if you think the duplicate status ',
                 'is wrong.',
                 '</div>'].join(''));
            container.insertBefore(duplicate_warning, first_node);
        }
    },

    /*
     * Ensure that no warning about adding a comment to a duplicate bug
     * is displayed.
     *
     * @method hide_comment_on_duplicate_warning
     */
    hide_comment_on_duplicate_warning: function() {
        var duplicate_warning = Y.one('#warning-comment-on-duplicate');
        if (duplicate_warning !== null) {
            duplicate_warning.ancestor().removeChild(duplicate_warning);
        }
    }
}, {
    HTML_PARSER: {
        // Look for the 'Mark as duplicate' links or the
        // 'change duplicate bug' link.
        update_dupe_link: '.menu-link-mark-dupe, #change_duplicate_bug',
        // The rendered duplicate information.
        dupe_span: '#mark-duplicate-text'
    },
    ATTRS: {
        io_provider: {

        },
        // The launchpad client entry for the current bug.
        lp_bug_entry: {
            value: null
        },
        // The link used to update the duplicate bug number.
        update_dupe_link: {
        },
        // The rendered duplicate information.
        dupe_span: {
        },
        // Div containing duplicates of this bug.
        duplicates_div: {
            getter: function() {
                return Y.one('#portlet-duplicates');
            }
        },
        // Override for testing.
        anim_duration: {
            value: 1
        }
    }
});

}, "0.1", {"requires": [
    "base", "io", "oop", "node", "event", "json", "lazr.formoverlay",
    "lazr.effects", "lp.app.widgets.expander",
    "lp.app.formwidgets.resizing_textarea", "plugin"]});
