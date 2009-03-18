YUI().add('lp.client.helpers', function (Y) {

Y.namespace('lp.client.helpers');
Y.lp.client.helpers.setBugTaskAssignee = function (
    bugtask_uri, assignee_name, cfg) {

    var client = new LP.client.Launchpad();
    var person_uri = LP.client.get_absolute_uri(
        '/~' + assignee_name, true);

    // Add parameter to cfg.
    if (cfg === undefined) {
        cfg = {};
    }
    cfg.parameters = {assignee: person_uri};

    // LP.client won't insert 'api/beta' into an absolute url.
    var index = bugtask_uri.indexOf('//');
    index = bugtask_uri.indexOf('/', index+2);
    bugtask_uri = bugtask_uri.substring(index);

    client.named_post(
        bugtask_uri,
        'transitionToAssignee',
        cfg);
};

}, '0.1', {requires: ['plugin', 'lazr.editor']});
