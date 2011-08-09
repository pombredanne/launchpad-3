/* Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
   GNU Affero General Public License version 3 (see the file LICENSE). */

YUI().use(
        'lp.testing.runner', 'test', 'console', 'node-event-simulate',
        'lp.soyuz.base', "lazr.anim", "lazr.formoverlay",
        'lp.soyuz.dynamic_dom_updater', 'event-simulate', "io-base",
        'lp.registry.distroseriesdifferences_details', function(Y) {

var suite = new Y.Test.Suite("Distroseries differences Tests");
var dsd_details = Y.lp.registry.distroseriesdifferences_details;
var dsd_uri = '/duntu/dwarty/+source/evolution/+difference/ubuntu/warty';

var first_row = [
    '<tr id="first_row" class="evolution">',
    '  <td>',
    '    <a href="/d/d/+source/evolution/+difference/ubuntu/warty"',
    '       class="js-action toggle-extra treeCollapsed ',
    '       sprite">evolution</a>',
    '  </td>',
    '  <td>',
    '    <a href="/ubuntu/warty" class="parent-name">Warty</a>',
    '  </td>',
    '  <td>',
    '    <a href="/ubuntu/warty/+source/evolution/2.0.9-1ubuntu2"',
    '       class="parent-version">',
    '       2.0.9-1ubuntu2</a>',
    '  </td>',
    '  <td>',
    '    <a href="/deribuntu/deriwarty/+source/evolution/2.0.8-4deribuntu1"',
    '       class="derived-version">',
    '       2.0.8-4deribuntu1</a>',
    '  </td>',
    '  <td class="packagesets"></td>',
    '  <td class="last-changed"></td>',
    '  <td class="latest-comment-fragment"></td>',
    '</tr>'
    ].join('');

var testExpandableRowWidget = {

    name: 'expandable-row-widget',

    setUp: function() {
        Y.one("#placeholder")
            .empty()
            .appendChild(Y.Node.create(first_row));
        this.toggle = Y.one('a.toggle-extra');
     },

    test_initializer: function() {
       var row = new dsd_details.ExpandableRowWidget({toggle: this.toggle});
       Y.Assert.isTrue(this.toggle.hasClass('treeCollapsed'));
       Y.Assert.isTrue(this.toggle.hasClass('sprite'));
    },

    test_parse_row_data: function() {
        var row = new dsd_details.ExpandableRowWidget({toggle: this.toggle});
        var parsed = row.parse_row_data();
        var res = {
            source_name: 'evolution',
            parent_series_name: 'warty',
            parent_distro_name: 'ubuntu',
            nb_columns: 7};
        Y.ObjectAssert.areEqual(res, parsed);
    },

    test_expander_handler_adds_new_row: function() {
        var row = new dsd_details.ExpandableRowWidget({toggle: this.toggle});
        row._toggle.simulate('click');
        var new_row = row._row.next();
        Y.Assert.isTrue(new_row.hasClass('evolution'));
        Y.Assert.isTrue(new_row.hasClass('diff-extra'));
        Y.Assert.areEqual(7, new_row.one('td').getAttribute('colspan'));
    },

    test_expand_handler_toggles_hiding: function() {
        var row = new dsd_details.ExpandableRowWidget({toggle: this.toggle});
        Y.Assert.isTrue(row._toggle.hasClass('treeCollapsed'));
        // First click opens up the new row.
        row._toggle.simulate('click');
        var new_row = row._row.next();
        Y.Assert.isTrue(row._toggle.hasClass('treeExpanded'));
        Y.Assert.isFalse(new_row.hasClass('unseen'));
        Y.Assert.isTrue(new_row.one('div').hasClass('diff-extra-container'));
        // Second click hides it.
        row._toggle.simulate('click');
        Y.Assert.isTrue(row._toggle.hasClass('treeCollapsed'));
        Y.Assert.isTrue(new_row.hasClass('unseen'));
    }

};

var blacklist_html = [
    '<div class="blacklist-options" style="float:left">',
    '  <dl>',
    '    <dt>Ignored:</dt>',
    '    <dd>',
    '      <form>',
    '        <div>',
    '          <div class="value">',
    '            <label for="field.blacklist_options.0">',
    '              <input type="radio" value="NONE" ',
    '                name="field.blacklist_options"',
    '                id="field.blacklist_options.0" checked="checked" ',
    '                class="radioType">&nbsp;No</input>',
    '            </label><br>',
    '            <label for="field.blacklist_options.1">',
    '              <input type="radio" value="BLACKLISTED_ALWAYS" ',
    '               name="field.blacklist_options"',
    '                id="field.blacklist_options.1" class="radioType">',
    '                &nbsp;All versions</input>',
    '            </label><br>',
    '            <label for="field.blacklist_options.2">',
    '              <input type="radio" value="BLACKLISTED_CURRENT"',
    '                name="field.blacklist_options"',
    '                id="field.blacklist_options.2"',
    '                class="radioType">&nbsp;These versions</input>',
    '            </label>',
    '          </div>',
    '          <input type="hidden" value="1" ',
    '            name="field.blacklist_options-empty-marker" />',
    '        </div>',
    '      </form>',
    '    </dd>',
    '  </dl>',
    '</div>'
    ].join('');

var second_row = [
    '<tr id="second_row">',
    '  <td>',
    '    <div class="diff-extra-container">',
    '      <div>',
    '      <dl>',
    '      <dt class="package-diff-placeholder">',
    '       <span class="package-diff-compute-request">',
    '        <a class="js-action sprite add" href="">',
    '          Compute differences from last common version:',
    '        </a>',
    '      </span></dt>',
    '      <dd>',
    '        <ul class="package-diff-status">',
    '          <li>',
    '            <span id="derived" class="PENDING">',
    '             1.2.1 to Derilucid version: 1.2.4',
    '            </span>',
    '          </li>',
    '          <li>',
    '            <span id="parent" class="request-derived-diff">',
    '              1.2.1 to Lucid version: 1.2.3',
    '            </span>',
    '          </li>',
    '        </ul>',
    '      </dd>',
    '      </dl>',
    '      </div>',
    blacklist_html,
    '      <div class="boardComment ">',
    '        <div class="boardCommentDetails">',
    '          <a class="sprite person" href="/~mark">Mark S.</a>',
    '          wrote on 2010-06-26',
    '        </div>',
    '        <div class="boardCommentBody">Body</div>',
    '      </div>',
    '      <div class="add-comment-placeholder evolution">',
    '        <a href="" class="widget-hd js-action sprite add">',
    '        Add comment</a>',
    '      </div>',
    '    </div>',
    '  </td>',
    '</tr>'
    ].join('');

var whole_table = [
    '<table class="listing"><tbody>',
    first_row,
    second_row,
    '</tbody></table>'
    ].join('');

var testPackageDiffUpdate = {

    name: 'package-diff',

    setUp: function() {
        Y.one("#placeholder")
            .empty()
            .appendChild(Y.Node.create(second_row));
    },

    test_vocabulary_helper: function() {
        // The vocabulary helper extracts the selected item from a
        // jsonified vocabulary.
        var voc = [
            {"token": "PENDING", "title": "Pending"},
            {"token": "COMPLETED", "selected": true, "title": "Completed"},
            {"token": "FAILED", "title": "Failed"}];
        var res = dsd_details.get_selected(voc);
        Y.Assert.areEqual('COMPLETED', res.token);
        Y.Assert.areEqual('Completed', res.title);
        var voc_nothing_selected = [
            {"token": "PENDING", "title": "Pending"},
            {"token": "COMPLETED", "title": "Completed"},
            {"token": "FAILED", "title": "Failed"}];
        Y.Assert.isUndefined(dsd_details.get_selected(voc_nothing_selected));
    },

    test_add_msg_node: function() {
        var msg_txt = 'Exemple text';
        var msg_node = Y.Node.create(msg_txt);
        placeholder = Y.one('#placeholder');
        dsd_details.add_msg_node(placeholder, msg_node);
        Y.Assert.areEqual(
            placeholder.one('.package-diff-placeholder').get('innerHTML'),
            msg_txt);
    }
};

var testBlacklistWidget = {

    name: 'package-diff-update-interaction',

    setUp: function() {
        Y.one("#placeholder")
            .empty()
            .appendChild(Y.Node.create(whole_table));
        this.node = Y.one('.blacklist-options');
        this.latestCommentContainer = Y.one('td.latest-comment-fragment');
        this.addCommentPlaceholder = Y.one('div.add-comment-placeholder');
        this.widget = new dsd_details.BlacklistWidget(
            {srcNode: this.node,
             sourceName: 'evolution',
             dsdLink: '/a/link',
             latestCommentContainer: this.latestCommentContainer,
             addCommentPlaceholder: this.addCommentPlaceholder});
     },

    test_initializer: function() {
        Y.Assert.areEqual(this.node, this.widget.get('srcNode'));
        Y.Assert.areEqual('evolution', this.widget.sourceName);
        Y.Assert.areEqual('/a/link', this.widget.dsdLink);
        Y.Assert.areEqual(
            this.latestCommentContainer,
            this.widget.latestCommentContainer);
        Y.Assert.areEqual(
            this.addCommentPlaceholder,
            this.widget.addCommentPlaceholder);
    },

    test_wire_blacklist_click: function() {
        var input = Y.one(
            'div.blacklist-options input[value="BLACKLISTED_CURRENT"]');
        var fired = false;

        var blacklist_comment_overlay = function(target) {
            fired = true;
            Y.Assert.areEqual(input, target);
        };
        this.widget.blacklist_comment_overlay = blacklist_comment_overlay;
        input.simulate('click');

        this.wait(function() {
            Y.Assert.isTrue(fired);
        }, 1000);
    },

    test_wire_blacklist_changed: function() {
        var fired = false;

        var blacklist_submit_handler = function(arg1, arg2, arg3, arg4) {
            fired = true;
            Y.Assert.areEqual(1, arg1);
            Y.Assert.areEqual(2, arg2);
            Y.Assert.areEqual(3, arg3);
            Y.Assert.areEqual(4, arg4);
        };
        this.widget.blacklist_submit_handler = blacklist_submit_handler;
        this.widget.fire('blacklist_changed', 1, 2, 3, 4);

        this.wait(function() {
            Y.Assert.isTrue(fired);
        }, 1000);
    },

    test_containing_rows: function() {
        var expected = [Y.one('#first_row'), Y.one('#second_row')];
        Y.ArrayAssert.itemsAreEqual(expected, this.widget.relatedRows);
    },

    test_blacklist_comment_overlay_creates_overlay: function() {
        var input = Y.one('div.blacklist-options input');
        var overlay = this.widget.blacklist_comment_overlay(input);
        // Check overlay's structure.
        Y.Assert.isInstanceOf(Y.lazr.FormOverlay, overlay);
        Y.Assert.isNotNull(overlay.form_node.one('textarea'));
        Y.Assert.areEqual(
            'OK',
            overlay.form_node.one('button[type="submit"]').get('text'));
        Y.Assert.areEqual(
            'Cancel',
            overlay.form_node.one('button[type="button"]').get('text'));
        Y.Assert.isTrue(overlay.get('visible'));
    },

    test_blacklist_comment_overlay_cancel_hides_overlay: function() {
        var input = Y.one('div.blacklist-options input');
        var overlay = this.widget.blacklist_comment_overlay(input);
        var cancel_button = overlay.form_node.one('button[type="button"]');
        Y.Assert.isTrue(overlay.get('visible'));
        cancel_button.simulate('click');
        Y.Assert.isFalse(overlay.get('visible'));
     },

    test_blacklist_comment_overlay_ok_hides_overlay: function() {
        var input = Y.one('div.blacklist-options input');
        var overlay = this.widget.blacklist_comment_overlay(input);
        Y.Assert.isTrue(overlay.get('visible'));
        overlay.form_node.one('button[type="submit"]').simulate('click');
        Y.Assert.isFalse(overlay.get('visible'));
    },

    test_blacklist_comment_overlay_fires_event: function() {
        var input = Y.one('div.blacklist-options input[value="NONE"]');
        input.set('checked', true);
        var overlay = this.widget.blacklist_comment_overlay(input);
        var event_fired = false;
        var method = null;
        var all = null;
        var comment = null;
        var target = null;

        var handleEvent = function(e, e_method, e_all, e_comment, e_target) {
            event_fired = true;
            method = e_method;
            all = e_all;
            comment = e_comment;
            target = e_target;
        };

        this.widget.on("blacklist_changed", handleEvent, this.widget);

        overlay.form_node.one('textarea').set('text', 'Test comment');
        overlay.form_node.one('button[type="submit"]').simulate('click');
        this.wait(function() {
            Y.Assert.isTrue(event_fired);
            Y.Assert.areEqual('unblacklist', method);
            Y.Assert.areEqual(false, all);
            Y.Assert.areEqual('Test comment', comment);
            Y.Assert.areEqual(input, target);
        }, 1000);
    },

    test_blacklist_comment_overlay_fires_event_blacklist_all: function() {
        var input = Y.one(
            'div.blacklist-options input[value="BLACKLISTED_ALWAYS"]');
        input.set('checked', true);
        var overlay = this.widget.blacklist_comment_overlay(input);
        var method = null;
        var all = null;
        var target = null;

        var handleEvent = function(e, e_method, e_all, e_comment, e_target) {
            method = e_method;
            all = e_all;
            target = e_target;
        };
        this.widget.on("blacklist_changed", handleEvent, this.widget);

        overlay.form_node.one('button[type="submit"]').simulate('click');
        this.wait(function() {
            Y.Assert.areEqual('blacklist', method);
            Y.Assert.areEqual(true, all);
            Y.Assert.areEqual(input, target);
        }, 1000);
    },

    test_blacklist_comment_overlay_fires_event_blacklist: function() {
        var input = Y.one(
            'div.blacklist-options input[value="BLACKLISTED_CURRENT"]');
        input.set('checked', true);
        var overlay = this.widget.blacklist_comment_overlay(input);
        var method = null;
        var all = null;
        var target = null;

        var handleEvent = function(e, e_method, e_all, e_comment, e_target) {
            method = e_method;
            all = e_all;
            target = e_target;
        };
        this.widget.on("blacklist_changed", handleEvent, this.widget);

        overlay.form_node.one('button[type="submit"]').simulate('click');
        this.wait(function() {
            Y.Assert.areEqual('blacklist', method);
            Y.Assert.areEqual(false, all);
            Y.Assert.areEqual(input, target);
        }, 1000);
    },

    assertAllDisabled: function(selector) {
        var all_input_status = Y.all(selector).get('disabled');
        Y.Assert.isTrue(all_input_status.every(function(val) {return val;}));
    },

    assertAllEnabled: function(selector) {
        var all_input_status = Y.all(selector).get('disabled');
        Y.Assert.isTrue(all_input_status.every(function(val) {return !val;}));
    },

    patchNamedPost: function(method_name, expected_parameters) {
        function Comment() {}
        Comment.prototype.get = function(key) {
            if (key === 'comment_date') {
                return "2011-08-08T13:15:50.636269+00:00";}
            if (key === 'body_text') {
                return 'This is the comment';}
            if (key === 'self_link') {
                return ["https://lp.net/api/devel/u/d//+source/",
                        "evolution/+difference/ubuntu/warty/comments/6"
                        ].join('');}
            if (key === 'web_link') {
                return ["https://lp.net/d/d/+source/evolution/",
                        "+difference/ubuntu/warty/comments/6"
                        ].join('');}
        };
        var comment_entry = new Comment();
        var self = this;
        dsd_details.lp_client.named_post = function(url, func, config) {
            Y.Assert.isNotNull(Y.one('img[src="/@@/spinner"]'));
            Y.Assert.areEqual(func, method_name);
            Y.ObjectAssert.areEqual(expected_parameters ,config.parameters);
            self.assertAllDisabled('div.blacklist-options input');
            config.on.success(comment_entry);
        };
    },

    assertBlacklisted: function(input, color) {
        Y.Assert.isTrue(input.get('checked'));
        Y.Assert.isNull(Y.one('img[src="/@@/spinner"]'));
       // Wait 2 seconds for the animation to run.
        this.wait(function() {
            Y.Assert.areEqual(
                color,
                Y.one('#first_row').getStyle('backgroundColor'));
            Y.Assert.areEqual(
                color,
                Y.one('#second_row').getStyle('backgroundColor'));
        }, 2000);
     },

    test_blacklist_submit_handler_blacklist_simple: function() {
        this.patchNamedPost(
            'blacklist',
            {comment: 'Test comment', all: false});
        var input = Y.one(
            'div.blacklist-options input[value="BLACKLISTED_CURRENT"]');
        input.set('checked', false);
        this.widget.blacklist_submit_handler(
            'blacklist', false, "Test comment", input);

        this.assertBlacklisted(input, 'rgb(238, 238, 238)');
        this.assertAllEnabled('div.blacklist-options input');
    },

    test_blacklist_submit_handler_blacklist_all: function() {
        this.patchNamedPost(
            'blacklist',
            {comment: 'Test comment', all: true});
        var input = Y.one(
            'div.blacklist-options input[value="BLACKLISTED_ALWAYS"]');
        input.set('checked', false);
        this.widget.blacklist_submit_handler(
            'blacklist', true, "Test comment", input);

        this.assertBlacklisted(input, 'rgb(238, 238, 238)');
        this.assertAllEnabled('div.blacklist-options input');
    },

    test_blacklist_submit_handler_unblacklist: function() {
        this.patchNamedPost(
            'unblacklist',
            {comment: 'Test comment', all: true});
        var input = Y.one('div.blacklist-options input[value="NONE"]');
        input.set('checked', false);
        this.widget.blacklist_submit_handler(
            'unblacklist', true, "Test comment", input);

        this.assertBlacklisted(input, 'rgb(255, 255, 255)');
        this.assertAllEnabled('div.blacklist-options input');
    },

    test_blacklist_submit_handler_failure: function() {
        var self = this;
        dsd_details.lp_client.named_post = function(url, func, config) {
            Y.Assert.isNotNull(Y.one('img[src="/@@/spinner"]'));
            self.assertAllDisabled('div.blacklist-options input');
            config.on.failure();
        };
        var input = Y.one('div.blacklist-options input');
        input.set('checked', false);
        this.widget.blacklist_submit_handler(
            null, 'unblacklist', true, "Test comment", input);

        Y.Assert.isNull(Y.one('img[src="/@@/spinner"]'));
        this.assertAllEnabled('div.blacklist-options input');
    }

};

var testPackageDiffUpdateInteraction = {

    name: 'package-diff-update-interaction',

    setUp: function() {
        Y.one("#placeholder")
            .empty()
            .appendChild(Y.Node.create(whole_table));
        var first_poll = true;
        pending_voc = [
            {"token": "PENDING", "selected": true, "title": "Pending"},
            {"token": "COMPLETED", "title": "Completed"},
            {"token": "FAILED", "title": "Failed"}];
        completed_voc = [
            {"token": "PENDING", "title": "Pending"},
            {"token": "COMPLETED", "selected": true, "title": "Completed"},
            {"token": "FAILED", "title": "Failed"}];

        // Monkey patch request.
        dsd_details.lp_client.named_post = function(url, func, config) {
            config.on.success();};
        dsd_details.lp_client.named_get = function(url, func, config) {
            config.on.success();};
        dsd_details.lp_client.get = function(uri, config) {
            if (first_poll === true) {
                first_poll = false;
                config.on.success(pending_voc);
            }
            else {
                config.on.success(completed_voc);
            }
        };
        dsd_details.poll_interval = 100;
    },

    test_request_wrong_click: function() {
        // Click on the placeholder has no effect.
        // The listeners are on the the link with class
        // '.package-diff-compute-request'.
        // bug=746277.
        var placeholder = Y.one('#placeholder');
        placeholder
            .one('#derived')
                .removeClass('PENDING')
                    .addClass('FAILED');
        dsd_details.setup_packages_diff_states(
            placeholder.one('.diff-extra-container'), dsd_uri);
        var func_req;
        dsd_details.lp_client.named_post = function(url, func, config) {
            func_req = func;
            config.on.success();
        };

        var wrong_button = placeholder.one('.package-diff-placeholder');

        wrong_button.simulate('click');
        var package_diff = Y.one('#parent');

        // The request has not been triggered.
        Y.Assert.isTrue(package_diff.hasClass('request-derived-diff'));
    },

    test_request_package_diff_computation: function() {
        // A click on the button changes the package diff status and requests
        // the package diffs computation via post.
        var placeholder = Y.one('#placeholder');
        placeholder
            .one('#derived')
            .removeClass('PENDING')
            .addClass('FAILED');
        dsd_details.setup_packages_diff_states(
            placeholder.one('.diff-extra-container'), dsd_uri);
        var func_req;
        dsd_details.lp_client.named_post = function(url, func, config) {
            func_req = func;
            config.on.success();
        };
        var button = placeholder.one('.package-diff-compute-request');

        button.simulate('click');
        var package_diff = Y.one('#parent');

        Y.Assert.isTrue(package_diff.hasClass('PENDING'));
        Y.Assert.isFalse(package_diff.hasClass('request-derived-diff'));
        Y.Assert.areEqual('requestPackageDiffs', func_req);
        Y.Assert.isNotUndefined(package_diff.updater);

        // Let the polling happen.
        this.wait(function() {
            Y.Assert.isTrue(package_diff.hasClass('PENDING'));
                this.wait(function() {
                    Y.Assert.isTrue(package_diff.hasClass('COMPLETED'));
                }, dsd_details.poll_interval);
         }, dsd_details.poll_interval);
    },

    test_polling_for_pending_items: function() {
        // The polling has started on the pending package diff. The
        // status is being updated.
        var placeholder = Y.one('#placeholder');
        dsd_details.setup_packages_diff_states(
            placeholder.one('.diff-extra-container'), dsd_uri);
        var package_diff = Y.one('#derived');
        Y.Assert.isTrue(package_diff.hasClass('PENDING'));
        Y.Assert.isFalse(package_diff.hasClass('request-derived-diff'));
        this.wait(function() {
            Y.Assert.isTrue(package_diff.hasClass('PENDING'));
                this.wait(function() {
                    Y.Assert.isTrue(package_diff.hasClass('COMPLETED'));
                }, dsd_details.poll_interval);
        }, dsd_details.poll_interval);
    }
};

suite.add(new Y.Test.Case(testPackageDiffUpdate));
suite.add(new Y.Test.Case(testExpandableRowWidget));
suite.add(new Y.Test.Case(testBlacklistWidget));
suite.add(new Y.Test.Case(testPackageDiffUpdateInteraction));

Y.lp.testing.Runner.run(suite);

});

