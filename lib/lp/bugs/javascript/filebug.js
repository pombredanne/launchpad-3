/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Provide functionality for the file bug pages.
 *
 * @module bugs
 * @submodule filebug
 */
YUI.add('lp.bugs.filebug', function(Y) {

var namespace = Y.namespace('lp.bugs.filebug');

// For tests.
var skip_animation;

var setup_filebug = function(skip_anim) {
    skip_animation = skip_anim;
    if (LP.cache.enable_bugfiling_duplicate_search) {
        Y.lp.bugs.filebug_dupefinder.setup_dupe_finder();
        Y.lp.bugs.filebug_dupefinder.setup_dupes();
    }
    var search_button = Y.one(Y.DOM.byId('field.actions.projectgroupsearch'));
    if (Y.Lang.isValue(search_button )) {
        search_button.set('value', 'Check again');
    }
    if (LP.cache.show_information_type_in_ui) {
        setup_information_type();
    } else {
        setup_security_related();
    }
    setupChoiceWidgets();
    var filebug_privacy_text = "This report will be private. " +
        "You can disclose it later.";
    update_privacy_banner(
        LP.cache.bug_private_by_default, filebug_privacy_text);
};

var update_privacy_banner = function(show, banner_text) {
    var banner = Y.lp.app.banner.privacy.getPrivacyBanner(
        banner_text, skip_animation);
    if (show) {
        banner.show();
    } else {
        banner.hide();
    }
};

var setup_information_type = function() {
    var itypes_table = Y.one('.radio-button-widget');
    itypes_table.delegate('click', function() {
        var private_type = (Y.Array.indexOf(
            LP.cache.private_types, this.get('value')) >= 0);
        update_privacy_banner(private_type);
    }, "input[name='field.information_type']");
};

var setupChoiceWidgets = function() {
    Y.lp.app.choice.addPopupChoice('status', LP.cache.bugtask_status_data);
    Y.lp.app.choice.addPopupChoice(
        'importance', LP.cache.bugtask_importance_data);
};

var setup_security_related = function() {
    var sec = Y.one('[id="field.security_related"]');
    if (!Y.Lang.isValue(sec)) {
        return;
    }
    var notification_text = "This report will be private " +
                           "because it is a security " +
                           "vulnerability. You can " +
                           "disclose it later.";
    sec.on('change', function() {
      var checked = sec.get('checked');
      update_privacy_banner(checked, notification_text);
    });
};

namespace.setup_filebug = setup_filebug;

}, "0.1", {"requires": [
    "base", "node", "event", "node-event-delegate", "lazr.choiceedit",
    "lp.app.banner.privacy", "lp.app.choice",
    "lp.bugs.filebug_dupefinder"]});
