/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Provide functionality for picking a bug.
 *
 * @module bugs
 * @submodule bug_picker
 */
YUI.add('lp.bugs.duplicates', function(Y) {

var namespace = Y.namespace('lp.bugs.duplicates');
var superclass = Y.lp.bugs.bug_picker.BugPicker;

/**
 * A widget to allow a user to choose a bug.
 * This widget does no rendering itself; it is used to enhance existing HTML.
 */
namespace.DuplicateBugPicker = Y.Base.create(
    "duplicateBugPickerWidget", Y.lp.bugs.bug_picker.BugPicker, [], {
    initializer: function(cfg) {
        this.lp_client = new Y.lp.client.Launchpad(cfg);
    },

    bindUI: function() {
        superclass.prototype.bindUI.apply(this, arguments);
        var that = this;
        this.subscribe(
            Y.lp.bugs.bug_picker.BugPicker.SAVE_DUPLICATE, function(e) {
            e.preventDefault();
            that.set('progress', 100);
            var bug_id = e.details[0];
            that._submit_bug(bug_id, this.save_button);
        });
        this.subscribe(
            Y.lp.bugs.bug_picker.BugPicker.REMOVE_DUPLICATE, function(e) {
            e.preventDefault();
            that.set('progress', 100);
            that._submit_bug('', this.remove_link);
        });
    },

    _bug_search_header: function() {
        var search_header = '<p class="search-header">' +
            'Marking this bug as a duplicate will, ' +
            'by default, hide it from search results listings.</p>';

        var duplicatesNode = this.get('duplicatesNode');
        if (Y.Lang.isValue(duplicatesNode)) {
            search_header +=
                '<p class="block-sprite large-warning">' +
                '<strong>Note:</strong> ' +
                'This bug has duplicates of its own. ' +
                'If you go ahead, they too will become duplicates of ' +
                'the bug you specify here.  This cannot be undone.' +
                '</p>';
        }
        return search_header +
            superclass.prototype._bug_search_header.call(this);
    },

    /**
     * Look up the selected bug and get the user to confirm that it is the one
     * they want.
     *
     * @param data
     * @private
     */
    _find_bug: function(data) {
        var new_dup_id = Y.Lang.trim(data.id);
        // Do some quick checks before we submit.
        var error = false;
        if (new_dup_id === LP.cache.bug.id.toString()) {
            this._hide_bug_results();
            this.set('error',
                'A bug cannot be marked as a duplicate of itself.');
            error = true;
        }
        var duplicate_of_link = LP.cache.bug.duplicate_of_link;
        var new_dupe_link
            = Y.lp.client.get_absolute_uri("/api/devel/bugs/" + new_dup_id);
        if (new_dupe_link === duplicate_of_link) {
            this._hide_bug_results();
            this.set('error',
                'This bug is already marked as a duplicate of bug ' +
                new_dup_id + '.');
            error = true;
        }
        if (error) {
            this.set('search_mode', false);
            return;
        }
        Y.lp.bugs.bug_picker.BugPicker.prototype._find_bug.call(this, data);
    },

    /**
     * Bug was successfully marked as a duplicate, update the UI.
     *
     * @method _submit_bug_success
     * @param updated_entry
     * @param new_dup_url
     * @param new_dup_id
     * @private
     */
    _submit_bug_success: function(updated_entry, new_dup_url,
                                           new_dup_id) {
        this._performDefaultSave();
        updated_entry.set('duplicate_of_link', new_dup_url);
        LP.cache.bug.duplicate_of_link = updated_entry.duplicate_of_link;
        this.set('lp_bug_entry', updated_entry);

        var dupe_span = this.get('dupe_span').ancestor('li');
        var update_dup_url = dupe_span.one('a').get('href');
        var edit_link;
        if (Y.Lang.isValue(new_dup_url)) {
            dupe_span.removeClass('sprite bug-dupe');
            dupe_span.setContent([
                '<a id="change_duplicate_bug" ',
                'title="Edit or remove linked duplicate bug" ',
                'class="sprite edit action-icon"',
                'style="margin-left: 0">Edit</a>',
                '<span id="mark-duplicate-text">',
                'Duplicate of <a>bug #</a></span>'].join(""));
            edit_link = dupe_span.one('#change_duplicate_bug');
            edit_link.set('href', update_dup_url);
            dupe_span.all('a').item(1)
                .set('href', '/bugs/' + new_dup_id)
                .appendChild(document.createTextNode(new_dup_id));
            var duplicatesNode = this.get('duplicatesNode');
            if (Y.Lang.isValue(duplicatesNode)) {
                duplicatesNode.remove(true);
            }
            this._show_comment_on_duplicate_warning();
        } else {
            dupe_span.addClass('sprite bug-dupe');
            dupe_span.setContent([
                '<span id="mark-duplicate-text">',
                '<a class="menu-link-mark-dupe js-action">',
                'Mark as duplicate</a></span>'].join(""));
            edit_link = dupe_span.one('a');
            edit_link.set('href', update_dup_url);
            this._hide_comment_on_duplicate_warning();
        }
        dupe_span = this.get('portletNode').one('#mark-duplicate-text');
        this.set('dupe_span', dupe_span);
        var anim_duration = 1;
        if (!this.get('use_animation')) {
            anim_duration = 0;
        }
        Y.lp.anim.green_flash({
            node: dupe_span,
            duration: anim_duration
            }).run();
        // ensure the new link is hooked up correctly:
        var that = this;
        edit_link.on(
            'click', function(e){
                e.preventDefault();
                that.show();
            });
    },

    /**
     * There was an error marking a bug as a duplicate.
     *
     * @method _submit_bug_failure
     * @param response
     * @param old_dup_url
     * @private
     */
    _submit_bug_failure: function(response, old_dup_url) {
        // Reset the lp_bug_entry.duplicate_of_link as it wasn't
        // updated.
        this.get('lp_bug_entry').set('duplicate_of_link', old_dup_url);
        var error_msg = response.responseText;
        if (response.status === 400) {
            var error_info = response.responseText.split('\n');
            error_msg = error_info.slice(1).join(' ');
        }
        this.set('error', error_msg);
    },

    /**
     * Update the bug duplicate via the LP API
     *
     * @method _submit_bug
     * @param new_dup_id
     * @param widget
     * @private
     */
    _submit_bug: function(new_dup_id, widget) {
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

        var new_dup_url = null;
        if (new_dup_id !== '') {
            var self_link = lp_bug_entry.get('self_link');
            var last_slash_index = self_link.lastIndexOf('/');
            new_dup_url = self_link.slice(0, last_slash_index+1) + new_dup_id;
        }
        var old_dup_url = lp_bug_entry.get('duplicate_of_link');
        lp_bug_entry.set('duplicate_of_link', new_dup_url);

        var dupe_span = this.get('dupe_span');
        var that = this;
        var spinner = null;
        var config = {
            on: {
                start: function() {
                    dupe_span.removeClass('sprite bug-dupe');
                    dupe_span.addClass('update-in-progress-message');
                    that.set('error', null);
                    spinner = that._show_bug_spinner(widget);
                },
                end: function() {
                    dupe_span.removeClass('update-in-progress-message');
                    if (spinner !== null) {
                        spinner.remove(true);
                    }
                },
                success: function(updated_entry) {
                    that._submit_bug_success(
                        updated_entry, new_dup_url, new_dup_id);
                },
                failure: function(id, response) {
                    that._submit_bug_failure(response, old_dup_url);
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
     * @method _show_comment_on_duplicate_warning
     * @private
     */
    _show_comment_on_duplicate_warning: function() {
        var duplicate_warning = Y.one('#warning-comment-on-duplicate');
        if (!Y.Lang.isValue(duplicate_warning)) {
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
     * @method _hide_comment_on_duplicate_warning
     * @private
     */
    _hide_comment_on_duplicate_warning: function() {
        var duplicate_warning = Y.one('#warning-comment-on-duplicate');
        if (duplicate_warning !== null) {
            duplicate_warning.ancestor().removeChild(duplicate_warning);
        }
    }
}, {
    ATTRS: {
        // The launchpad client entry for the current bug.
        lp_bug_entry: {
            value: null
        },
        // The rendered duplicate information.
        dupe_span: {
            getter: function() {
                return Y.one('#mark-duplicate-text');
            }
        },
        // Div containing duplicates of this bug.
        duplicatesNode: {
            getter: function() {
                return Y.one('#portlet-duplicates');
            }
        },
        portletNode: {
            getter: function() {
                return Y.one('#duplicate-actions');
            }
        },
        header_text: {
           value: 'Mark bug report as duplicate'
        },
        save_link_text: {
            value: 'Save Duplicate'
        },
        remove_link_text: {
            value: 'Bug is not a duplicate'
        },
        remove_link_visible: {
            getter: function() {
                var existing_dupe = LP.cache.bug.duplicate_of_link;
                return Y.Lang.isString(existing_dupe) && existing_dupe !== '';
            }
        },
        private_warning_message: {
            value:
            'Marking this bug as a duplicate of a private bug means '+
            'that it won\'t be visible to contributors and encourages '+
            'the reporting of more duplicate bugs.<br>' +
            'Perhaps there is a public bug that can be used instead.'
        }
    }
});

}, "0.1", {"requires": [
    "base", "io", "oop", "node", "event", "json",
    "lp.bugs.bug_picker"]});
