/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Information Type choice widget for bug pages.
 */

YUI.add('lp.bugs.information_type_choice', function(Y) {

var namespace = Y.namespace('lp.bugs.information_type_choice');
/* XXX 05-11-2012 j.c.sackett This whole module could be rewritten as an
 * extension of Y.Base, which would provide the option of setting lp_client
 * and privacy banner as attributes, rather than having to pass them from
 * function to function.
 */
namespace.save_information_type = function(value, lp_client, privacy_banner) {
    var error_handler = new Y.lp.client.ErrorHandler();
    var config = {
        on: {
            success: function(id, response) {
                namespace.information_type_save_success(
                    value,
                    privacy_banner);
            },
            failure: error_handler.getFailureHandler()
        },
        parameters: {
            information_type: value
        }
    };
    lp_client.named_post(
        LP.cache.bug.self_link, 'transitionToInformationType', config);
};

namespace.information_type_save_success = function(value, privacy_banner) {
    var body = Y.one('body');
    var private_type = (Y.Array.indexOf(LP.cache.private_types, value) >= 0);
    var subscription_ns = Y.lp.bugs.bugtask_index.portlets.subscription;
    subscription_ns.update_subscription_status();
    if (private_type) {
        body.replaceClass('public', 'private');
        privacy_banner.show();
    } else {
        body.replaceClass('private', 'public');
        privacy_banner.hide();
    }
};

var setup_func = function(privacy_link, lp_client, privacy_banner) {
    var information_type = Y.one('#information-type');
    var information_type_edit = new Y.ChoiceSource({
        editicon: privacy_link,
        contentBox: Y.one('#privacy'),
        value_location: information_type,
        value: LP.cache.bug.information_type,
        title: "Change information type",
        items: LP.cache.information_types,
        backgroundColor: '#FFFF99'
    });
    information_type_edit.render();
    information_type_edit.on("save", function(e) {
        var value = information_type_edit.get('value');
        // This is required due to the display_userdata_as_private feature
        // flag.
        if (value === 'Private') {
            value = 'User Data';
        }
        namespace.save_information_type(value, lp_client, privacy_banner);
    });
    privacy_link.addClass('js-action');
};
namespace.setup_information_type_choice = setup_func;
}, "0.1", {"requires": ["base", "oop", "node", "event", "io-base",
                        "lazr.choiceedit", "lp.app.banner.privacy",
                        "lp.bugs.bugtask_index"]});
