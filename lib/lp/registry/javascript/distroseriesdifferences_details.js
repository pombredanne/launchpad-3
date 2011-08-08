/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Enhancements for the distroseries differences page.
 *
 * @module registry
 * @submodule distroseriesdifferences_details
 * @requires  io-base, lp.soyuz.base
 */
YUI.add('lp.registry.distroseriesdifferences_details', function(Y) {

var namespace = Y.namespace('lp.registry.distroseriesdifferences_details');

/**
 * Create one Launchpad client that will be used with multiple requests.
 */
namespace.lp_client = new Y.lp.client.Launchpad();

namespace.io = Y.io;

/*
 * XXX: rvb 2011-08-01 bug=796669: At present this module it is
 * function-passing spaghetti. The duct-tape is getting frayed.
 * It ought to be recomposed as widgets or something a bit more objecty so
 * it can be unit tested without having to set-up the world each time.
 */

function ExpandableRowWidget(config) {
    ExpandableRowWidget.superclass.constructor.apply(this, arguments);
}

ExpandableRowWidget.NAME = "expandableRowWidget";

Y.extend(ExpandableRowWidget, Y.Base, {
    initializer: function(cfg) {
        this._toggle = cfg.toggle;
        this._row = this._toggle.ancestor('tr');
        this._toggle.addClass('treeCollapsed').addClass('sprite');
        this._toggle.on("click", this.expander_handler, this);
    },

    parse_row_data: function() {
        var source_name = this._row.one('a.toggle-extra').get('text');
        var rev_link = this._row
            .one('a.toggle-extra').get('href').split('/').reverse();
        var parent_series_name = rev_link[0];
        var parent_distro_name = rev_link[1];
        var nb_columns = this._row.all('td').size();
        var res = {
            source_name: source_name,
            parent_series_name: parent_series_name,
            parent_distro_name: parent_distro_name,
            nb_columns: nb_columns};
        return res;
    },

    expander_handler: function(e) {
        e.preventDefault();
        parsed = this.parse_row_data();
        this._toggle.toggleClass('treeCollapsed').toggleClass('treeExpanded');

        // Only insert if there isn't already a container row there.
        var detail_row = this._row.next();
        if (detail_row === null ||
            !detail_row.hasClass('diff-extra')) {
            details_row = Y.Node.create([
                '<table><tr class="diff-extra unseen ',
                parsed.source_name + '">',
                '  <td colspan="'+parsed.nb_columns+'">',
                '    <div class="diff-extra-container"></div>',
                '  </td></tr></table>'
                ].join('')).one('tr');
            this._row.insert(details_row, 'after');
            var uri = this._toggle.get('href');
            this.get_extra_diff_info(
                uri, this._row, details_row.one('td'), parsed.source_name,
                parsed.parent_distro_name, parsed.parent_series_name);
        }
        details_row.toggleClass('unseen');
    },

    setup_extra_diff_info: function(master_container, container,
                                    source_name, parent_distro_name,
                                    parent_series_name, response) {
        container.one('div.diff-extra-container').insert(
            response.responseText, 'replace');
        var api_uri = [
            LP.cache.context.self_link,
            '+source',  source_name, '+difference',
            parent_distro_name, parent_series_name
           ].join('/');
        var latest_comment_container =
            master_container.one('td.latest-comment-fragment');
        // The add comment slot is only available when the user has the
        // right to add comments.
        var add_comment_placeholder =
            container.one('div.add-comment-placeholder');
        if (add_comment_placeholder !== null) {
           namespace.setup_add_comment(
                add_comment_placeholder,
                latest_comment_container,
                api_uri);
        }
        // The blacklist slot with a class 'blacklist-options' is only
        // available when the user has the right to blacklist.
        var blacklist_slot = container.one('div.blacklist-options');

        if (blacklist_slot !== null) {
            var blacklist_widget = new BlacklistWidget(
                {srcNode: blacklist_slot,
                 sourceName: source_name,
                 dsdLink: api_uri,
                 latestCommentContainer: latest_comment_container,
                 addCommentPlaceholder: add_comment_placeholder});
        }
        // If the user has not the right to blacklist, we disable
        // the blacklist slot.
        var disabled_blacklist_slot = container.one(
            'div.blacklist-options-disabled');
        if (disabled_blacklist_slot !== null) {
            disabled_blacklist_slot
                .all('input').set('disabled', 'disabled');
        }
        // Set-up diffs and the means to request them.
        namespace.setup_packages_diff_states(container, api_uri);
    },

    /**
     * Get the extra information for this diff to display.
     *
     * @param uri {string} The uri for the extra diff info.
     * @param master_container {Node}
     *     The node that triggered the load of the extra info.
     * @param container {Node}
     *     A node which must contain a div with the class
     *     'diff-extra-container' into which the results are inserted.
     * @param source_name {String}
     *     The name of the source package for which diff info is desired.
     * @param parent_distro_name {String}
     *     The name of the distribution in which a different version of
     *     the source package exists.
     * @param parent_series_name {String}
     *     The name of the distroseries in which a different version of
     *     the source package exists.
     */
    get_extra_diff_info: function(uri, master_container, container,
                                  source_name, parent_distro_name,
                                  parent_series_name) {
        var in_progress_message = Y.lp.soyuz.base.makeInProgressNode(
            'Fetching difference details ...');
        container.one('div.diff-extra-container').insert(
            in_progress_message, 'replace');
        var success_cb = function(transaction_id, response, args) {
            this.setup_extra_diff_info(
                master_container, container, source_name, parent_distro_name,
                parent_series_name, response);
        };

        var failure_cb = function(transaction_id, response, args) {
            var retry_handler = function(e) {
                e.preventDefault();
                this.get_extra_diff_info(
                    args.uri, args.master_container, args.container,
                    args.source_name, args.parent_distro_name,
                    args.parent_series_name);
            };
            var failure_message = Y.lp.soyuz.base.makeFailureNode(
                'Failed to fetch difference details.', retry_handler);
            container.insert(failure_message, 'replace');

            var anim = Y.lazr.anim.red_flash({
                 node: args.container
                 });
            anim.run();
        };

        var config = {
            headers: {'Accept': 'application/json;'},
            context: this,
            on: {
                'success': success_cb,
                'failure': failure_cb
            },
            "arguments": {
                'master_container': master_container,
                'container': container,
                'uri': uri,
                'source_name': source_name
            }
        };
        namespace.io(uri, config);

    }
});

namespace.ExpandableRowWidget = ExpandableRowWidget;

/**
 * BlacklistWidget: the widget used by each row to control the
 * 'blacklisted' status of the DSD.
 */
function BlacklistWidget(config) {
    BlacklistWidget.superclass.constructor.apply(this, arguments);
}

BlacklistWidget.NAME = "blacklistWidget";

Y.augment(BlacklistWidget, Y.EventTarget);

BlacklistWidget.HTML_PARSER = {
    relatedRows: function(srcNode) {
        return [
            srcNode.ancestor('tr').previous(),
            srcNode.ancestor('tr')
            ];
    }
};

Y.extend(BlacklistWidget, Y.Widget, {
    initializer: function(cfg) {
        this.srcNode = cfg.srcNode;
        this.sourceName = cfg.sourceName;
        this.dsdLink = cfg.dsdLink;
        this.latestCommentContainer = cfg.latestCommentContainer;
        this.addCommentPlaceholder = cfg.addCommentPlaceholder;
        this.relatedRows = cfg.relatedRows;
        this.container = cfg.container;
        this.wire();
    },

    wire: function() {
        // Wire the click on blacklist form.
        var handleClick = function(e) {
            e.preventDefault();
            var target = e.target;
            this.blacklist_comment_overlay(target);
        };
        Y.on("click", handleClick, this.srcNode.all('input'), this);

        // Wire the ok event from the comment overlay.
        var handleBlacklistChange = function(e, method_name, blacklist_all,
                                             comment, target) {
            e.preventDefault();
            this.blacklist_submit_handler(
                method_name, blacklist_all, comment, target);
         };
        this.on("blacklist_changed", handleBlacklistChange,
            this);
    },

    /**
     * Popup an overlay to let the user enter an optionnal comment.
     *
     * @param target {Node}
     *     The target input node that was clicked.
     */
    blacklist_comment_overlay: function(target) {
        var comment_form = Y.Node.create("<form />")
            .appendChild(Y.Node.create("<textarea></textarea>")
                .set("name", "comment")
                .set("rows", "3")
                .set("cols", "60"));
        /* Buttons */
        var submit_button = Y.Node.create(
            '<button type="submit" class="lazr-pos lazr-btn" />')
                .set("text", "OK");
        var cancel_button = Y.Node.create(
            '<button type="button" class="lazr-neg lazr-btn" />')
                .set("text", "Cancel");

        var self = this;
        var submit_callback = function(data) {
            overlay.hide();
            // Get the comment string.
            var comment = "";
            if (data.comment !== undefined) {
                comment = data.comment[0];
            }
            // Figure out the new 'ignored' status.
            var value = target.get('value');
            var method_name = (value === 'NONE') ?
                'unblacklist' : 'blacklist';
            var blacklist_all = (
                target.get('value') === 'BLACKLISTED_ALWAYS');
            self.fire(
                'blacklist_changed', method_name, blacklist_all, comment,
                target);
        };
        var overlay = new Y.lazr.FormOverlay({
            align: {
                /* Align the centre of the overlay with the centre of the
                node containing the blacklist options. */
                node: this.srcNode,
                points: [
                    Y.WidgetPositionAlign.CC,
                    Y.WidgetPositionAlign.CC]
            },
            headerContent: "<h2>Add an optional comment</h2>",
            form_content: comment_form,
            form_submit_button: submit_button,
            form_cancel_button: cancel_button,
            form_submit_callback: submit_callback,
            visible: true
        });
        overlay.render();
        return overlay;
    },

    /**
     * Popup an overlay to let the user enter an optionnal comment.
     *
     * @param method_name {String}
     *     'blacklist' or 'unblacklist'.
     * @param blacklist_all {Boolean}
     *     Is this a blacklist all versions or blacklist current (only
     *     relevant if method_name is 'blacklist').
     * @param comment {String}
     *     The comment string.
     * @param target {Node}
     *     The target input node that was clicked.
     */
     blacklist_submit_handler: function(method_name, blacklist_all, comment,
                                        target) {
        // Disable all the inputs.
        this.srcNode.all('input').set('disabled', 'disabled');
        this.srcNode.prepend('<img src="/@@/spinner" />');

        //var diff_rows = Y.all('tr.' + source_name);
        var diff_rows = this.relatedRows;

        var self = this;
        var config = {
            on: {
                success: function(updated_entry, args) {
                    // Let the user know this item is now blacklisted.
                    self.srcNode.one('img').remove();
                    self.srcNode.all(
                        'input').set('disabled', false);
                    target.set('checked', true);
                    Y.each(diff_rows, function(diff_row) {
                        var fade_to_gray = new Y.Anim({
                            node: diff_row,
                            from: { backgroundColor: '#FFFFFF'},
                            to: { backgroundColor: '#EEEEEE'}
                        });
                        if (method_name === 'unblacklist') {
                            fade_to_gray.set('reverse', true);
                        }
                        fade_to_gray.run();
                        });
                    namespace.add_comment(
                        updated_entry, self.addCommentPlaceholder,
                        self.latestCommentContainer);
                },
                failure: function(id, response) {
                    self.srcNode.one('img').remove();
                    self.srcNode.all(
                        'input').set('disabled', false);
                }
            },
            parameters: {
                all: blacklist_all,
                comment: comment
            }
        };
        namespace.lp_client.named_post(this.dsdLink, method_name, config);
    }
});

namespace.BlacklistWidget = BlacklistWidget;

/**
 * Update the latest comment on the difference row.
 *
 * @param comment_entry {lp.client.Entry} An object representing
 *     a DistroSeriesDifferenceComment.
 * @param placeholder {Node}
 *     The node in which to put the latest comment HTML fragment. The
 *     contents of this node will be replaced.
 */
namespace.update_latest_comment = function(comment_entry, placeholder) {
    var comment_latest_fragment_url =
        comment_entry.get('web_link') + "/+latest-comment-fragment";
    var config = {
        on: {
            success: function(comment_latest_fragment_html) {
                placeholder.set(
                    "innerHTML", comment_latest_fragment_html);
                Y.lazr.anim.green_flash({node: placeholder}).run();
            },
            failure: function(id, response) {
                Y.lazr.anim.red_flash({node: placeholder}).run();
            }
        },
        accept: Y.lp.client.XHTML
    };
    namespace.lp_client.get(comment_latest_fragment_url, config);
};

/**
 * This method adds a comment in the UI. It appends a comment to the
 * list of comments and updates the latest comments slot.
 *
 * @param comment_entry {Comment} A comment as returns by the api.
 * @param add_comment_placeholder {Node} The node that contains the
 *     relevant comment fields.
 * @param latest_comment_placeholder {Node} The node that contains the
 *     latest comment.
 */
namespace.add_comment = function(comment_entry, add_comment_placeholder,
                                latest_comment_placeholder) {
    // Grab the XHTML representation of the comment
    // and prepend it to the list of comments.
    var config = {
        on: {
            success: function(comment_html) {
                var comment_node = Y.Node.create(comment_html);
                add_comment_placeholder.insert(comment_node, 'before');
                var reveal = Y.lazr.effects.slide_out(comment_node);
                reveal.on("end", function() {
                    Y.lazr.anim.green_flash(
                        {node: comment_node}).run();
                });
                reveal.run();
            }
        },
        accept: Y.lp.client.XHTML
    };
    namespace.lp_client.get(comment_entry.get('self_link'), config);
    namespace.update_latest_comment(
        comment_entry, latest_comment_placeholder);
};

/**
 * Handle the add comment event triggered by the 'add comment' form.
 *
 * This method adds a comment via the API and update the UI.
 *
 * @param comment_form {Node} The node that contains the relevant comment
 *     fields.
 * @param latest_comment_placeholder {Node} The node that contains the
 *     latest comment.
 * @param api_uri {string} The uri for the distroseriesdifference to which
 *     the comment is to be added.
 * @param cb_success {function} Called when a comment has successfully
 *     been added. (Deferreds would be awesome right about now.)
 */
namespace.add_comment_handler = function(comment_form,
                                         latest_comment_placeholder, api_uri,
                                         cb_success) {
    var comment_area = comment_form.one('textarea');
    var comment_text = comment_area.get('value');

    // Treat empty comments as mistakes.
    if (Y.Lang.trim(comment_text).length === 0) {
        Y.lazr.anim.red_flash({node: comment_area}).run();
        return;
    }

    var success_handler = function(comment_entry) {
        namespace.add_comment(
            comment_entry, comment_form, latest_comment_placeholder);
        comment_form.one('textarea').set('value', '');
        cb_success();
    };
    var failure_handler = function(id, response) {
        // Re-enable field with red flash.
        Y.lazr.anim.red_flash({node: comment_form}).run();
    };

    var config = {
        on: {
            success: success_handler,
            failure: failure_handler,
            start: function() {
                // Show a spinner.
                comment_form.one('div.widget-bd')
                    .append('<img src="/@@/spinner" />');
                // Disable the textarea and button.
                comment_form.all('textarea,button')
                    .setAttribute('disabled', 'disabled');
            },
            end: function() {
                // Remove the spinner.
                comment_form.all('img').remove();
                // Enable the form.
                comment_form.all('textarea,button')
                    .removeAttribute('disabled');
            }
        },
        parameters: {
            comment: comment_text
        }
    };
    namespace.lp_client.named_post(api_uri, 'addComment', config);
};

/**
 * Add the comment fields ready for sliding out.
 *
 * This method adds the markup for a slide-out comment and sets
 * the event handlers.
 *
 * @param placeholder {Node} The node that is to contain the comment
 *     fields.
 * @param api_uri {string} The uri for the distroseriesdifference to which
 *     the comment is to be added.
 */
namespace.setup_add_comment = function(placeholder,
                                       latest_comment_placeholder,
                                       api_uri) {
    placeholder.insert([
        '<a class="widget-hd js-action sprite add" href="">',
        '  Add comment</a>',
        '<div class="widget-bd lazr-closed" ',
        '     style="height:0;overflow:hidden">',
        '  <textarea></textarea><button>Save comment</button>',
        '</div>'
        ].join(''), 'replace');

    // The comment area should slide in when the 'Add comment'
    // action is clicked.
    var slide_anim = null;
    var slide = function(direction) {
        // Slide out if direction is true, slide in if direction
        // is false, otherwise do the opposite of what's being
        // animated right now.
        if (slide_anim === null) {
            slide_anim = Y.lazr.effects.slide_out(
                placeholder.one('div.widget-bd'));
            if (Y.Lang.isBoolean(direction)) {
                slide_anim.set("reverse", !direction);
            }
        }
        else {
            if (Y.Lang.isBoolean(direction)) {
                slide_anim.set("reverse", !direction);
            }
            else {
                slide_anim.set('reverse', !slide_anim.get('reverse'));
            }
            slide_anim.stop();
        }
        slide_anim.run();
    };
    var slide_in = function() { slide(false); };

    placeholder.one('a.widget-hd').on(
        'click', function(e) { e.preventDefault(); slide(); });
    placeholder.one('button').on('click', function(e) {
        e.preventDefault();
        namespace.add_comment_handler(
            placeholder, latest_comment_placeholder,
            api_uri, slide_in);
    });
};

namespace.setup = function() {
    Y.all('table.listing a.toggle-extra').each(function(toggle){
        var row = new namespace.ExpandableRowWidget({toggle: toggle});
    });
};

var set_package_diff_status = function(container, new_status, note_msg) {
    container.removeClass('request-derived-diff');
    container.removeClass('PENDING');
    note = container.all('.note').remove();
    container.addClass(new_status);
    if (note_msg !== undefined) {
        container.append([
            '<span class="note greyed-out">(',
            note_msg,
            ')</span>'].join(''));
    }
};

/*
* Helper function to extract the selected state from a jsonified
* Vocabulary.
*
* @param json_voc {object} A jsonified Vocabulary
*
*/
namespace.get_selected = function(json_voc) {
    var i;
    for (i = 0; i < json_voc.length; i++) {
        var obj = json_voc[i];
        if (obj.selected === true) {
            return obj;
        }
    }
    return undefined;
};

namespace.add_link_to_package_diff = function(container, url_uri) {
    var y_config = {
        headers: {'Accept': 'application/json;'},
        on: {
            success: function(url) {
                container.all('.update-failure-message').remove();
                container
                    .wrap('<a />')
                    .ancestor()
                        .set("href", url);
            },
            failure: function(url) {
                container.all('.update-failure-message').remove();

                var retry_handler = function(e) {
                    e.preventDefault();
                    namespace.add_link_to_package_diff(container, url_uri);
                };
                var failure_message = Y.lp.soyuz.base.makeFailureNode(
                    'Failed to fetch package diff url.', retry_handler);
                container.insert(failure_message);
            }
        }
    };
    namespace.lp_client.named_get(url_uri , null, y_config);
};

/**
* Polling intervall for checking package diff's status.
*/
namespace.poll_interval = 30000;

/**
* Attach package diff status poller.
*
* This method attachs a poller to the container to check
* the package diff object's status.
*
* @param container {Node} The container node displaying this package
*     diff information.
* @param dsd_link {string} The uri for the distroseriesdifference object.
*/
namespace.setup_pending_package_diff = function(container, dsd_link) {
    var parent = container.hasClass('parent');
    var package_diff_uri = [
        dsd_link,
        parent ? 'parent_package_diff_status' : 'package_diff_status'
        ].join('/');
    var build_package_diff_update_config = {
        uri: package_diff_uri,
        lp_client: namespace.lp_client,
        parent: parent,
        /**
        * This function knows how to update a package diff status.
        *
        * @config domUpdateFunction
        */
        domUpdateFunction: function(container, data_object) {
            var state_and_name = namespace.get_selected(data_object);
            var state = state_and_name.token;
            var name = state_and_name.title;
            if (state === 'FAILED') {
                set_package_diff_status(container, 'FAILED', name);
                Y.lazr.anim.red_flash({node: container}).run();
             }
            else if (state === 'COMPLETED') {
                set_package_diff_status(container, 'COMPLETED');
                url_uri = [
                    dsd_link,
                    parent ? 'parent_package_diff_url' : 'package_diff_url'
                    ].join('/');
                namespace.add_link_to_package_diff(container, url_uri);
                Y.lazr.anim.green_flash({node: container}).run();
             }
        },

        interval: namespace.poll_interval,

        /**
        * This function knows whether the package diff status
        * should stop being updated. It checks whether the state
        * is COMPLETED or FAILED.
        *
        * @config stopUpdatesCheckFunction
        */
        stopUpdatesCheckFunction: function(container){
            if (container.hasClass("COMPLETED")) {
                return true;
            }
            else if (container.hasClass("FAILED")) {
                return true;
            }
            else {
                return false;
            }
        }
    };
    container.plug(Y.lp.soyuz.dynamic_dom_updater.DynamicDomUpdater,
        build_package_diff_update_config);
};


/**
* Add a button to start package diff computation.
*
* @param row {Node} The container node for this package extra infos.
* @param dsd_link {string} The uri for the distroseriesdifference object.
*/
namespace.setup_request_derived_diff = function(container, dsd_link) {
    // Setup handler for diff requests. There should either zero or
    // one clickable node.
    container.all('.package-diff-compute-request').on('click', function(e) {
        e.preventDefault();
        namespace.compute_package_diff(container, dsd_link);
    });
};

/**
* - Add a button to start package diff computation (if needed).
* - Start pollers for pending packages diffs.
*
* @param row {Node} The container node for this package extra infos.
* @param dsd_link {string} The uri for the distroseriesdifference object.
*/
namespace.setup_packages_diff_states = function(container, dsd_link) {
    // Attach pollers for pending packages diffs.
    container.all('.PENDING').each(function(sub_container){
        namespace.setup_pending_package_diff(sub_container, dsd_link);
    });
    // Set-up the means to request a diff.
    namespace.setup_request_derived_diff(container, dsd_link);
};

/**
* Helper method to add a message node inside the placeholder.
*
* @param container {Node} The container in which to look for the
*     placeholder.
* @param msg_node {Node} The message node to add.
*/
namespace.add_msg_node = function(container, msg_node) {
    container.one('.package-diff-placeholder')
        .empty()
        .appendChild(msg_node);
};

/**
* Start package diff computation. Update package diff status to PENDING.
*
* @param row {Node} The container node for this package diff.
* @param dsd_link {string} The uri for the distroseriesdifference object.
*/
namespace.compute_package_diff = function(container, dsd_link) {
    var in_progress_message = Y.lp.soyuz.base.makeInProgressNode(
        'Computing package diff...');
    namespace.add_msg_node(container, in_progress_message);
    var success_cb = function(transaction_id, response, args) {
        container.one('p.update-in-progress-message').remove();
        container.one('.package-diff-placeholder').set(
            'text',
            'Differences from last common version:');
        container.all('.request-derived-diff').each(function(sub_container) {
            set_package_diff_status(sub_container, 'PENDING', 'Pending');
            // Setup polling
            namespace.setup_pending_package_diff(sub_container, dsd_link);
            var anim = Y.lazr.anim.green_flash({
                node: sub_container
            });
            anim.run();
        });
    };
    var failure_cb = function(transaction_id, response, args) {
        container.one('p.update-in-progress-message').remove();
        var recompute = function(e) {
            e.preventDefault();
            namespace.compute_package_diff(container, dsd_link);
        };

        var msg = response.responseText;

        // If the error is not of the type raised by an error properly
        // raised by python then set a standard error message.
        if (response.status !== 400) {
            msg = 'Failed to compute package diff.';
        }
        var failure_msg = Y.lp.soyuz.base.makeFailureNode(msg, recompute);
        namespace.add_msg_node(container, failure_msg);
    };
    var config = {
        on: {
            'success': success_cb,
            'failure': failure_cb
        },
        "arguments": {
            'container': container,
            'dsd_link': dsd_link
        }
    };
    namespace.lp_client.named_post(dsd_link, 'requestPackageDiffs', config);
};

}, "0.1", {"requires": ["io-base", "widget", "event", "overlay",
                        "lp.soyuz.base", "lp.client",
                        "lazr.anim", "lazr.formoverlay",
                        "lp.soyuz.dynamic_dom_updater"]});
