import os

import pytest

import puppetboard.core
from puppetboard import docker_settings

try:
    import future.utils
except:
    pass

try:
    from importlib import reload as reload
except:
    pass


@pytest.fixture(scope='function')
def cleanUpEnv(request):
    for env_var in dir(docker_settings):
        if (env_var.startswith('__') or env_var.startswith('_') or
                env_var.islower()):
            continue

        if env_var in os.environ:
            del os.environ[env_var]
    reload(docker_settings)
    return


def test_default_host_port(cleanUpEnv):
    assert docker_settings.PUPPETDB_HOST == 'puppetdb'
    assert docker_settings.PUPPETDB_PORT == 8080


def test_set_host_port(cleanUpEnv):
    os.environ['PUPPETDB_HOST'] = 'puppetdb2'
    os.environ['PUPPETDB_PORT'] = '9081'
    reload(docker_settings)
    assert docker_settings.PUPPETDB_HOST == 'puppetdb2'
    assert docker_settings.PUPPETDB_PORT == 9081


def test_set_proto(cleanUpEnv):
    os.environ['PUPPETDB_PROTO'] = 'https'
    reload(docker_settings)
    assert docker_settings.PUPPETDB_PROTO == 'https'


def test_cert_true_test(cleanUpEnv):
    os.environ['PUPPETDB_SSL_VERIFY'] = 'True'
    reload(docker_settings)
    assert docker_settings.PUPPETDB_SSL_VERIFY is True
    os.environ['PUPPETDB_SSL_VERIFY'] = 'true'
    reload(docker_settings)
    assert docker_settings.PUPPETDB_SSL_VERIFY is True


def test_cert_false_test(cleanUpEnv):
    os.environ['PUPPETDB_SSL_VERIFY'] = 'False'
    reload(docker_settings)
    assert docker_settings.PUPPETDB_SSL_VERIFY is False
    os.environ['PUPPETDB_SSL_VERIFY'] = 'false'
    reload(docker_settings)
    assert docker_settings.PUPPETDB_SSL_VERIFY is False


def test_cert_path(cleanUpEnv):
    ca_file = '/usr/ssl/path/ca.pem'
    os.environ['PUPPETDB_SSL_VERIFY'] = ca_file
    reload(docker_settings)
    assert docker_settings.PUPPETDB_SSL_VERIFY == ca_file


def validate_facts(facts):
    assert isinstance(facts, list)
    assert len(facts) > 0
    for map in facts:
        assert isinstance(map, tuple)
        assert len(map) == 2


def test_inventory_facts_default(cleanUpEnv):
    validate_facts(docker_settings.INVENTORY_FACTS)


def test_invtory_facts_custom(cleanUpEnv):
    os.environ['INVENTORY_FACTS'] = "A, B, C, D"
    reload(docker_settings)
    validate_facts(docker_settings.INVENTORY_FACTS)


def test_graph_facts_defautl(cleanUpEnv):
    facts = docker_settings.GRAPH_FACTS
    assert isinstance(facts, list)
    assert 'puppetversion' in facts


def test_graph_facts_custom(cleanUpEnv):
    os.environ['GRAPH_FACTS'] = "architecture, puppetversion, extra"
    reload(docker_settings)
    facts = docker_settings.GRAPH_FACTS
    assert isinstance(facts, list)
    assert len(facts) == 3
    assert 'puppetversion' in facts
    assert 'architecture' in facts
    assert 'extra' in facts


def test_bad_log_value(cleanUpEnv, mocker):
    os.environ['LOGLEVEL'] = 'g'
    os.environ['PUPPETBOARD_SETTINGS'] = '../puppetboard/docker_settings.py'
    reload(docker_settings)

    puppetboard.core.APP = None
    with pytest.raises(ValueError) as error:
        puppetboard.core.get_app()


def test_default_table_selctor(cleanUpEnv):
    assert [10, 20, 50, 100, 500] == docker_settings.TABLE_COUNT_SELECTOR


def test_env_table_selector(cleanUpEnv):
    os.environ['TABLE_COUNT_SELECTOR'] = '5,15,25'
    reload(docker_settings)
    assert [5, 15, 25] == docker_settings.TABLE_COUNT_SELECTOR


def test_env_column_options(cleanUpEnv):
    os.environ['DISPLAYED_METRICS'] = 'resources.total, events.failure'

    reload(docker_settings)
    assert ['resources.total',
            'events.failure'] == docker_settings.DISPLAYED_METRICS
