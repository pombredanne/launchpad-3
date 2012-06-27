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
    }
    Y.lp.bugs.filebug_dupefinder.setup_dupes();
    // Only attempt to wire up the file bug form if the form is rendered.
    var filebugform = Y.one('#filebug-form');
    var bugreportingform = Y.one('#bug-reporting-form');
    if (Y.Lang.isValue(filebugform) || Y.Lang.isValue(bugreportingform)) {
        var search_button =
            Y.one(Y.DOM.byId('field.actions.projectgroupsearch'));
        if (Y.Lang.isValue(search_button )) {
            search_button.set('value', 'Check again');
        }
        setup_information_type();
        setupChoiceWidgets();
    }
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

var get_new_banner_text = function(value) {
    var info_type_descriptions = {
        EMBARGOEDSECURITY: 'Embargoed Security',
        USERDATA: 'User Data',
        PROPRIETARY: 'Proprietary'
    };

    if (LP.cache.show_userdata_as_private) {
        info_type_descriptions.USERDATA = 'Private';
    }
    var text_template = "This report has {info_type} information." +
        " You can change the information type later.";
    value = info_type_descriptions[value];
    return Y.Lang.substitute(text_template, {'info_type': value});
};

var setup_information_type = function() {
    var itypes_table = Y.one('.radio-button-widget');
    itypes_table.delegate('change', function() {
        var banner_text = get_new_banner_text(this.get('value'));
        var private_type = (Y.Array.indexOf(
            LP.cache.private_types, this.get('value')) >= 0);

        update_privacy_banner(private_type, banner_text);
    }, "input[name='field.information_type']");
};

var setupChoiceWidgets = function() {
    Y.lp.app.choice.addPopupChoice('status', LP.cache.bugtask_status_data);
    Y.lp.app.choice.addPopupChoice(
        'importance', LP.cache.bugtask_importance_data);
    Y.lp.app.choice.addPopupChoiceForRadioButtons(
        'information_type', LP.cache.information_type_data, true);
};

namespace.setup_filebug = setup_filebug;

}, "0.1", {"requires": [
    "base", "node", "event", "node-event-delegate", "lazr.choiceedit",
    "lp.app.banner.privacy", "lp.app.choice",
    "lp.bugs.filebug_dupefinder"]});
