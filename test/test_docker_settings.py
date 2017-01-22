import os
from puppetboard import docker_settings
import unittest
import tempfile
try:
    import future.utils
except:
    pass

try:
    from imp import reload as reload
except:
    pass


class DockerTestCase(unittest.TestCase):
    def setUp(self):
        for env_var in dir(docker_settings):
            if (env_var.startswith('__') or env_var.startswith('_') or
                    env_var.islower()):
                continue

            if env_var in os.environ:
                del os.environ[env_var]
        reload(docker_settings)

    def test_default_host_port(self):
        self.assertEqual(docker_settings.PUPPETDB_HOST, 'puppetdb')
        self.assertEqual(docker_settings.PUPPETDB_PORT, 8080)

    def test_set_host_port(self):
        os.environ['PUPPETDB_HOST'] = 'puppetdb'
        os.environ['PUPPETDB_PORT'] = '9081'
        reload(docker_settings)
        self.assertEqual(docker_settings.PUPPETDB_HOST, 'puppetdb')
        self.assertEqual(docker_settings.PUPPETDB_PORT, 9081)

    def test_cert_true_test(self):
        os.environ['PUPPETDB_SSL_VERIFY'] = 'True'
        reload(docker_settings)
        self.assertTrue(docker_settings.PUPPETDB_SSL_VERIFY)
        os.environ['PUPPETDB_SSL_VERIFY'] = 'true'
        reload(docker_settings)
        self.assertTrue(docker_settings.PUPPETDB_SSL_VERIFY)

    def test_cert_false_test(self):
        os.environ['PUPPETDB_SSL_VERIFY'] = 'False'
        reload(docker_settings)
        self.assertFalse(docker_settings.PUPPETDB_SSL_VERIFY)
        os.environ['PUPPETDB_SSL_VERIFY'] = 'false'
        reload(docker_settings)
        self.assertFalse(docker_settings.PUPPETDB_SSL_VERIFY)

    def test_cert_path(self):
        ca_file = '/usr/ssl/path/ca.pem'
        os.environ['PUPPETDB_SSL_VERIFY'] = ca_file
        reload(docker_settings)
        self.assertEqual(docker_settings.PUPPETDB_SSL_VERIFY, ca_file)

    def validate_facts(self, facts):
        self.assertEqual(type(facts), type([]))
        self.assertTrue(len(facts) > 0)
        for map in facts:
            self.assertEqual(type(map), type(()))
            self.assertTrue(len(map) == 2)

    def test_inventory_facts_default(self):
        self.validate_facts(docker_settings.INVENTORY_FACTS)

    def test_invtory_facts_custom(self):
        os.environ['INVENTORY_FACTS'] = "A, B, C, D"
        reload(docker_settings)
        self.validate_facts(docker_settings.INVENTORY_FACTS)

    def test_graph_facts_defautl(self):
        facts = docker_settings.GRAPH_FACTS
        self.assertEqual(type(facts), type([]))
        self.assertTrue('puppetversion' in facts)

    def test_graph_facts_custom(self):
        os.environ['GRAPH_FACTS'] = "architecture, puppetversion, extra"
        reload(docker_settings)
        facts = docker_settings.GRAPH_FACTS
        self.assertEqual(type(facts), type([]))
        self.assertEqual(len(facts), 3)
        self.assertTrue('puppetversion' in facts)
        self.assertTrue('architecture' in facts)
        self.assertTrue('extra' in facts)


if __name__ == '__main__':
    unittest.main()
