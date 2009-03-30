from canonical.launchpad.windmill.testing import lpuser

from windmill.authoring import WindmillTestClient

def test_confirm_subscription():
    """Test the confirm subscription action for subscribers.

    This test ensurens that with Javascript enabled, the 'Confirm
    subscription' link uses the formoverlay to post the activation directly,
    removing one page load.
    """
    client = WindmillTestClient("P3a confirm subscription test")

    # Currently all the p3a subscription work is hidden behind admin,
    # so login as foo.bar and activate our ppa.
    lpuser.FOO_BAR.ensure_login(client)
    client.open(url='http://launchpad.dev:8085/~name16/+activate-ppa')
    client.check(id=u'field.accepted')
    client.click(id=u'field.actions.activate')
    client.waits.forPageLoad(timeout=u'20000')

    # The PPA also needs to be private to use archive subscriptions:
    client.waits.forElement(link=u'Administer archive', timeout=u'8000')
    client.click(link=u'Administer archive')
    client.waits.forPageLoad(timeout=u'20000')
    client.check(id=u'field.private')
    client.click(id=u'field.buildd_secret')
    client.type(text=u'secret', id=u'field.buildd_secret')
    client.click(id=u'field.actions.save')
    client.waits.forPageLoad(timeout=u'20000')

    # Now add ourselves as a subscriber (as we don't have any other admins
    # to test with).
    client.open(
        url='http://launchpad.dev:8085/~name16/+archive/ppa/+subscriptions')
    client.click(id=u'field.subscriber')
    client.type(text=u'name16', id=u'field.subscriber')
    client.click(id=u'field.actions.add')
    client.waits.forPageLoad(timeout=u'20000')

    # Next, look at all the private archive subscriptions for foobar
    client.open(
        url='http://launchpad.dev:8085/~name16/+archivesubscriptions')

    # Click on the Confirm now link... this brings up the form overlay
    client.click(link=u'                  Confirm now                 ')

    # Click on the form overlay's 'activate' button.
    client.click(name=u'activate')
    client.waits.forPageLoad(timeout=u'20000')

    # Now the subscription has been confirmed.
    client.asserts.assertNode(xpath=u"//div[@id='container']/div[3]/h1")
    client.asserts.assertText(xpath=u"//div[@id='container']/div[3]/h1",
        validator=u"Foo Bar's subscription to Private PPA for Foo Bar")

