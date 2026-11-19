from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.checks import check_allowed_hosts, check_toss_secret_key


class ProductionCheckTests(SimpleTestCase):
    def test_nfr12_production_needs_allowed_hosts(self):
        with self.assertRaises(ImproperlyConfigured):
            check_allowed_hosts(debug=False, hosts=[])
        check_allowed_hosts(debug=False, hosts=["example.test"])
        check_allowed_hosts(debug=True, hosts=[])

    def test_nfr13_only_test_toss_keys(self):
        with self.assertRaises(ImproperlyConfigured):
            check_toss_secret_key("live_sk_abc")
        with self.assertRaises(ImproperlyConfigured):
            check_toss_secret_key("sk_abc")
        self.assertTrue(check_toss_secret_key("test_sk_abc"))
        self.assertFalse(check_toss_secret_key(""))
