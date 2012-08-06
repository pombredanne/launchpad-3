/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Provide functionality for picking a bug.
 *
 * @module bugs
 * @submodule bug_picker
 */
YUI.add('lp.bugs.bug_picker', function(Y) {

var namespace = Y.namespace('lp.bugs.bug_picker');

// Overlay related vars.
var find_button_html =
    '<button type="submit" name="field.actions.find"' +
    '>Find Duplicate</button>';
var save_button_html =
    '<button type="button" name="field.actions.save"' +
    '>Save Duplicate</button>';

/**
 * A widget to allow a user to choose a bug.
 * This widget does no rendering itself; it is used to enhance existing HTML.
 */
namespace.BugPicker = Y.Base.create("bugPickerWidget", Y.Widget, [], {
    initializer: function(cfg) {
        this.lp_client = new Y.lp.client.Launchpad(cfg);
        this.io_provider = Y.lp.client.get_configured_io_provider(cfg);
        var select_bug_link = cfg.select_bug_link;
        if (select_bug_link) {
            // Add a class denoting the link as js-action link.
            select_bug_link.addClass('js-action');
        }
    },

    _remove_link_html: function() {
        return [
            '<div class="centered">',
            '<a class="sprite remove ',
            'js-action" href="javascript:void(0)">',
            this.get('remove_link_text'),
            '</a></div>'].join('');
    },

    renderUI: function() {
        var select_bug_link = this.get('select_bug_link');
        if (!Y.Lang.isValue(select_bug_link)) {
            return;
        }
        // Pre-load the mark-dupe form.
        var mark_dupe_form_url =
            select_bug_link.get('href') + '/++form++';

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
        form_header = form_header + this._remove_link_html();

        this.find_button = Y.Node.create(find_button_html);
        this.picker_form = new Y.lazr.FormOverlay({
            headerContent: '<h2>Mark bug report as duplicate</h2>',
            form_header: form_header,
            form_submit_button: this.find_button,
            form_cancel_button: undefined,
            centered: true,
            // The form submit first searches for the bug.
            form_submit_callback:
                    Y.bind(this._find_bug, this),
            visible: false,
            io_provider: this.io_provider,
            show_close_button: true
        });
        this.picker_form.render('#duplicate-form-container');
        this.picker_form.loadFormContentAndRender(mark_dupe_form_url);
    },

    bindUI: function () {
        // Add an on-click handler to any links found that displays
        // the form overlay.
        var select_bug_link = this.get('select_bug_link');
        if (!Y.Lang.isValue(select_bug_link)) {
            return;
        }
        var that = this;
        select_bug_link.on('click', function(e) {
            // Only go ahead if we have received the form content by the
            // time the user clicks:
            if (that.picker_form) {
                e.halt();
                that.picker_form.show();
                Y.DOM.byId('field.duplicateof').focus();
            }
        });
        // Wire up the Remove link.
        this.picker_form.after('contentUpdate', function() {
            var remove_link = that.picker_form.form_header_node
                .one('a.remove');
            if (Y.Lang.isValue(remove_link)) {
                remove_link.on('click', function(e) {
                    e.halt();
                    that._submit_bug('');
                });
            }
        });
        // When the dupe form overlay is hidden, we need to reset the form.
        this.picker_form.after('visibleChange', function() {
            if (!this.get('visible')) {
                that._hide_bug_details_node();
            } else {
                Y.DOM.byId('field.duplicateof').value = '';
                var remove_link = that.picker_form.form_header_node
                    .one('a.remove');
                var existing_dupe = LP.cache.bug.duplicate_of_link;
                if (Y.Lang.isString(existing_dupe) && existing_dupe !== '') {
                    remove_link.removeClass('hidden');
                } else {
                    remove_link.addClass('hidden');
                }
            }
        });
    },

    /**
     * Show a spinner next to the specified node.
     *
     * @method _show_bug_spinner
     * @private
     */
    _show_bug_spinner: function(node) {
        if( !Y.Lang.isValue(node)) {
            return null;
        }
        var spinner_node = Y.Node.create(
        '<img class="spinner" src="/@@/spinner" alt="Searching..." />');
        node.insert(spinner_node, 'after');
        return spinner_node;
    },

    /**
     * Look up the selected bug and get the user to confirm that it is the one
     * they want.
     *
     * @param data
     * @private
     */
    _find_bug: function(data) {
        var new_dup_id = Y.Lang.trim(data['field.duplicateof'][0]).trim();
        // If there's no bug data entered then we are deleting the duplicate
        // link.
        if (new_dup_id === '') {
            this.picker_form.showError(
                'Please enter a valid bug number.');
            return;
        }

        // Do some quick checks before we submit.
        if (new_dup_id === LP.cache.bug.id.toString()) {
            this._hide_bug_details_node();
            this.picker_form.showError(
                'A bug cannot be marked as a duplicate of itself.');
            return;
        }
        var duplicate_of_link = LP.cache.bug.duplicate_of_link;
        var new_dupe_link
            = Y.lp.client.get_absolute_uri("/api/devel/bugs/" + new_dup_id);
        if (new_dupe_link === duplicate_of_link) {
            this._hide_bug_details_node();
            this.picker_form.showError(
                'This bug is already marked as a duplicate of bug ' +
                new_dup_id + '.');
            return;
        }

        var that = this;
        var qs_data
            = Y.lp.client.append_qs("", "ws.accept", "application.json");
        qs_data = Y.lp.client.append_qs(qs_data, "ws.op", "getBugData");
        qs_data = Y.lp.client.append_qs(qs_data, "bug_id", new_dup_id);

        var bug_field = this.picker_form.form_node
            .one('[id="field.duplicateof"]');
        var spinner = null;
        var config = {
            on: {
                start: function() {
                    spinner = that._show_bug_spinner(bug_field);
                    that.picker_form.clearError();
                },
                end: function() {
                    if (spinner !== null) {
                        spinner.remove(true);
                    }
                },
                success: function(id, response) {
                    if (response.responseText === '') {
                        return;
                    }
                    var bug_data = Y.JSON.parse(response.responseText);
                    if (!Y.Lang.isArray(bug_data) || bug_data.length === 0) {
                        var error_msg =
                            new_dup_id + ' is not a valid bug number.';
                        that.picker_form.showError(error_msg);
                        return;
                    }
                    // The server may return multiple bugs but for now we only
                    // support displaying one of them.
                    that._confirm_selected_bug(bug_data[0]);
                },
                failure: function(id, response) {
                    that.picker_form.showError(response.responseText);
                }
            },
            data: qs_data
        };
        var uri
            = Y.lp.client.get_absolute_uri("/api/devel/bugs");
        this.io_provider.io(uri, config);
    },

    // Template for rendering the bug details.
    _bug_details_template: function() {
        return [
        '<table><tbody><tr><td>',
        '<div id="client-listing">',
        '  <div class="buglisting-col1">',
        '      <div class="importance {{importance_class}}">',
        '          {{importance}}',
        '      </div>',
        '      <div class="status {{status_class}}">',
        '          {{status}}',
        '      </div>',
        '      <div class="buginfo-extra">',
        '              <div class="information_type">',
        '                  {{information_type}}',
        '              </div>',
        '      </div>',
        '  </div>',
        '  <div class="buglisting-col2" style="max-width: 60em;">',
        '      <a href="{{bug_url}}" class="bugtitle sprite new-window">',
        '      <span class="bugnumber">#{{id}}</span>&nbsp;{{bug_summary}}</a>',
        '      <div class="buginfo-extra">',
        '          <p class="ellipsis line-block" style="max-width: 70em;">',
        '          {{description}}</p>',
        '      </div>',
        '  </div>',
        '</div></td></tr>',
        '{{> private_warning}}',
        '</tbody></table>'
        ].join(' ');
    },

    _private_warning_template: function(message) {
        var template = [
        '{{#private_warning}}',
        '<tr><td><p id="privacy-warning" ',
        'class="block-sprite large-warning">',
        '{message}',
        '</p></td></tr>',
        '{{/private_warning}}'
        ].join(' ');
        return Y.Lang.substitute(template, {message: message});
    },

    // Template for the bug confirmation form.
    _bug_confirmation_form_template: function() {
        return [
            '<div class="bug-details-node" ',
            'style="margin-top: 6px;">',
            '{{> bug_details}}',
            '</div>'].join('');
    },

    /**
     * Ask the user to confirm the chosen bug is the one they want.
     * @param bug_data
     * @private
     */
    _confirm_selected_bug: function(bug_data) {
        var bug_id = bug_data.id;
        bug_data.private_warning
            = this.get('public_context') && bug_data.is_private;
        var private_warning_message
            = this.get('private_warning_message');
        var html = Y.lp.mustache.to_html(
            this._bug_confirmation_form_template(), bug_data,
            {
                bug_details: this._bug_details_template(),
                private_warning:
                    this._private_warning_template(private_warning_message)
            });
        var that = this;
        var bug_details_node = Y.Node.create(html);
        var bug_link = bug_details_node.one('.bugtitle');
        bug_link.on('click', function(e) {
            e.halt();
            window.open(bug_link.get('href'));
        });
        this._show_bug_details_node(bug_details_node);
        this.save_button
            .on('click', function(e) {
                e.halt();
                that._submit_bug(bug_id);
            });
    },

    // Centre the duplicate form along the x axis without changing y position.
    _xaxis_centre: function() {
        var viewport = Y.DOM.viewportRegion();
        var new_x = (viewport.right  + viewport.left)/2 -
            this.picker_form.get('contentBox').get('offsetWidth')/2;
        this.picker_form.move([new_x, this.picker_form._getY()]);

    },

    /** Show the bug details node.
     * @method _show_bug_details_node
     * @private
     */
    _show_bug_details_node: function(new_bug_details_node) {
        var form = this.picker_form.form_node.one('.form');
        form.insert(new_bug_details_node, 'after');

        if(Y.Lang.isValue(this.bug_details_node)) {
            this.bug_details_node.remove(true);
        }
        if (!Y.Lang.isValue(this.save_button)) {
            this.save_button = this.find_button.insertBefore(
                Y.Node.create(save_button_html), this.find_button);
            this.find_button.set('text', 'Search Again');
        } else {
            this.save_button.detachAll();
        }
        var use_animation = this.get('use_animation');
        if (!use_animation) {
            this.bug_details_node = new_bug_details_node;
            return;
        }
        new_bug_details_node.addClass('transparent');
        new_bug_details_node.setStyle('opacity', 0);
        var fade_in = new Y.Anim({
            node: new_bug_details_node,
            to: {opacity: 1},
            duration: 0.8
        });
        var that = this;
        fade_in.on('end', function() {
            that.bug_details_node = new_bug_details_node;
        });
        fade_in.run();
        this._xaxis_centre();
    },

    /** Hide the bug details node.
     * @method _hide_bug_details_node
     * @private
     */
    _hide_bug_details_node: function() {
        if(Y.Lang.isValue(this.bug_details_node)) {
            this.bug_details_node.remove(true);
        }
        this.picker_form.clearError();
        this.bug_details_node = null;
        Y.DOM.byId('field.duplicateof').value = '';
        this._xaxis_centre();
        if (Y.Lang.isValue(this.save_button)) {
            this.save_button.detachAll();
            this.save_button.remove(true);
            this.save_button = null;
            this.find_button.set('text', 'Find Duplicate');
        }
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
        this.picker_form.hide();
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
            var duplicates_div = this.get('duplicates_div');
            if (Y.Lang.isValue(duplicates_div)) {
                duplicates_div.remove(true);
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
        dupe_span = this.get('srcNode').one('#mark-duplicate-text');
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
                that.picker_form.show();
                Y.DOM.byId('field.duplicateof').focus();
            });
    },

    /**
     * There was an error marking a bug as a duplicate.
     *
     * @method _submit_bug
     * @param response
     * @param old_dup_url
     * @param new_dup_id
     * @private
     */
    _submit_bug_failure: function(response, old_dup_url, new_dup_id) {
        // Reset the lp_bug_entry.duplicate_of_link as it wasn't
        // updated.
        this.get('lp_bug_entry').set('duplicate_of_link', old_dup_url);
        var error_msg = response.responseText;
        if (response.status === 400) {
            var error_info = response.responseText.split('\n');
            error_msg = error_info.slice(1).join(' ');
        }
        this.picker_form.showError(error_msg);
        this._xaxis_centre();
    },

    /**
     * Update the bug duplicate via the LP API
     *
     * @method _submit_bug
     * @param new_dup_id
     * @private
     */
    _submit_bug: function(new_dup_id) {
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
                    that.picker_form.clearError();
                    spinner = that._show_bug_spinner(that.save_button);
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
                    that._submit_bug_failure(
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
    HTML_PARSER: {
        // Look for the 'Mark as duplicate' links or the
        // 'change duplicate bug' link.
        select_bug_link: '.menu-link-mark-dupe, #change_duplicate_bug',
        // The rendered duplicate information.
        dupe_span: '#mark-duplicate-text'
    },
    ATTRS: {
        // Is the context in which this form being used public.
        public_context: {
            getter: function() {
                return !Y.one(document.body).hasClass('private');
            }
        },
        // Warning to display if we select a private bug from a public context.
        private_warning_message: {
            value: 'You are selecting a private bug.'
        },
        // The launchpad client entry for the current bug.
        lp_bug_entry: {
            value: null
        },
        // The link used to update the duplicate bug number.
        select_bug_link: {
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
        // The text used for the remove link.
        remove_link_text: {
            value: "Remove this bug"
        },
        // Override for testing.
        use_animation: {
            value: true
        }
    }
});

}, "0.1", {"requires": [
    "base", "io", "oop", "node", "event", "json", "lazr.formoverlay",
    "lazr.effects", "lp.app.widgets.expander", "lp.mustache",
    "lp.app.formwidgets.resizing_textarea", "plugin"]});
