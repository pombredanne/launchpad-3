/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Setup for managing subscribers list for questions.
 *
 * @module answers
 * @submodule subscribers
 */

YUI.add('lp.answers.answercontacts', function(Y) {

var namespace = Y.namespace('lp.answers.answercontacts');

/**
 * Create the SubscribersLoader instance which will load answer contacts for
 * a question and put them in the web page.
 */
function createQuestionAnswerContactsLoader(setup_config) {
    var questiontarget = {
        self_link: LP.cache.context.self_link,
        web_link: LP.cache.context.web_link };
    var default_config = {
        container_box: '#answer-contacts',
        subscribers_details_view:
            '/+portlet-answercontacts-details',
        subscriber_levels: {},
        context: questiontarget,
        display_me_in_list: true,
        subscribers_label: 'answer contacts',
        unsubscribe_label: 'Remove',
        unsubscribe_api: 'removeAnswerContact'
        };
    var module = Y.lp.app.subscribers.subscribers_list;

    if (Y.Lang.isValue(setup_config)) {
        setup_config = Y.mix(setup_config, default_config);
    } else {
        setup_config = default_config;
    }
    return new module.SubscribersLoader(setup_config);
}
namespace.createQuestionAnswerContactsLoader
    = createQuestionAnswerContactsLoader;

}, "0.1", {"requires": ["lp.app.subscribers.subscribers_list"]});
