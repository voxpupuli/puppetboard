import os

import pytest

from puppetboard import docker_settings

from importlib import reload as reload


@pytest.fixture(scope='function')
def cleanup_env(request):
    for env_var in dir(docker_settings):
        if (env_var.startswith('__') or env_var.startswith('_') or
                env_var.islower()):
            continue

        if env_var in os.environ:
            del os.environ[env_var]
    reload(docker_settings)
    return


def test_default_host_port(cleanup_env):
    assert docker_settings.PUPPETDB_HOST == 'puppetdb'
    assert docker_settings.PUPPETDB_PORT == 8080


def test_set_host_port(cleanup_env):
    os.environ['PUPPETDB_HOST'] = 'puppetdb2'
    os.environ['PUPPETDB_PORT'] = '9081'
    reload(docker_settings)
    assert docker_settings.PUPPETDB_HOST == 'puppetdb2'
    assert docker_settings.PUPPETDB_PORT == 9081


def test_set_proto(cleanup_env):
    os.environ['PUPPETDB_PROTO'] = 'https'
    reload(docker_settings)
    assert docker_settings.PUPPETDB_PROTO == 'https'


def test_cert_true_test(cleanup_env):
    os.environ['PUPPETDB_SSL_VERIFY'] = 'True'
    reload(docker_settings)
    assert docker_settings.PUPPETDB_SSL_VERIFY is True
    os.environ['PUPPETDB_SSL_VERIFY'] = 'true'
    reload(docker_settings)
    assert docker_settings.PUPPETDB_SSL_VERIFY is True


def test_cert_false_test(cleanup_env):
    os.environ['PUPPETDB_SSL_VERIFY'] = 'False'
    reload(docker_settings)
    assert docker_settings.PUPPETDB_SSL_VERIFY is False
    os.environ['PUPPETDB_SSL_VERIFY'] = 'false'
    reload(docker_settings)
    assert docker_settings.PUPPETDB_SSL_VERIFY is False


def test_cert_path(cleanup_env):
    ca_file = '/usr/ssl/path/ca.pem'
    os.environ['PUPPETDB_SSL_VERIFY'] = ca_file
    reload(docker_settings)
    assert docker_settings.PUPPETDB_SSL_VERIFY == ca_file


def test_cert_to_file(cleanup_env):
    import tempfile
    cert_string = '-----BEGIN CERTIFICATE-----\nMIIFkjCCA3qgAwf'

    os.environ['PUPPETDB_KEY'] = cert_string
    reload(docker_settings)
    assert docker_settings.PUPPETDB_KEY.startswith(tempfile.gettempdir())

    with open(docker_settings.PUPPETDB_KEY) as test_cert_file:
        assert test_cert_file.read() == '-----BEGIN CERTIFICATE-----\nMIIFkjCCA3qgAwf'

    # Clean up the generated file
    os.unlink(docker_settings.PUPPETDB_KEY)


def test_cert_to_file_base64(cleanup_env):
    import tempfile
    cert_string = 'LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUZrakNDQTNxZ0F3SUI='

    os.environ['PUPPETDB_KEY'] = cert_string
    reload(docker_settings)
    assert docker_settings.PUPPETDB_KEY.startswith(tempfile.gettempdir())

    with open(docker_settings.PUPPETDB_KEY) as test_cert_file:
        assert test_cert_file.read() == '-----BEGIN CERTIFICATE-----\nMIIFkjCCA3qgAwIB'

    # Clean up the generated file
    os.unlink(docker_settings.PUPPETDB_KEY)


def validate_facts(facts):
    assert isinstance(facts, list)
    assert len(facts) > 0
    for map in facts:
        assert isinstance(map, tuple)
        assert len(map) == 2


def test_inventory_facts_default(cleanup_env):
    validate_facts(docker_settings.INVENTORY_FACTS)


def test_invtory_facts_custom(cleanup_env):
    os.environ['INVENTORY_FACTS'] = "A, B, C, D"
    reload(docker_settings)
    validate_facts(docker_settings.INVENTORY_FACTS)


def test_inventory_fact_tempaltes_default(cleanup_env):
    assert isinstance(docker_settings.INVENTORY_FACT_TEMPLATES, dict)
    assert len(docker_settings.INVENTORY_FACT_TEMPLATES) == 3


def test_inventory_fact_tempaltes_custom(cleanup_env):
    os.environ['INVENTORY_FACT_TEMPLATES'] = """{"os": "{{ fact_os_detection(value) }}"}"""
    reload(docker_settings)

    assert isinstance(docker_settings.INVENTORY_FACT_TEMPLATES, dict)
    assert len(docker_settings.INVENTORY_FACT_TEMPLATES) == 1


def test_graph_facts_defautl(cleanup_env):
    facts = docker_settings.GRAPH_FACTS
    assert isinstance(facts, list)
    assert 'puppetversion' in facts


def test_graph_facts_custom(cleanup_env):
    os.environ['GRAPH_FACTS'] = "architecture, puppetversion, extra"
    reload(docker_settings)
    facts = docker_settings.GRAPH_FACTS
    assert isinstance(facts, list)
    assert len(facts) == 3
    assert 'puppetversion' in facts
    assert 'architecture' in facts
    assert 'extra' in facts


def test_default_table_selctor(cleanup_env):
    assert [10, 20, 50, 100, 500] == docker_settings.TABLE_COUNT_SELECTOR


def test_env_table_selector(cleanup_env):
    os.environ['TABLE_COUNT_SELECTOR'] = '5,15,25'
    reload(docker_settings)
    assert [5, 15, 25] == docker_settings.TABLE_COUNT_SELECTOR


def test_env_column_options(cleanup_env):
    os.environ['DISPLAYED_METRICS'] = 'resources.total, events.failure'

    reload(docker_settings)
    assert ['resources.total',
            'events.failure'] == docker_settings.DISPLAYED_METRICS


def test_enable_class_default(cleanup_env):
    assert False == docker_settings.ENABLE_CLASS

    
def test_enable_class_true(cleanup_env):
    os.environ['ENABLE_CLASS'] = 'True'
    reload(docker_settings)
    assert docker_settings.ENABLE_CLASS is True
    os.environ['ENABLE_CLASS'] = 'true'
    reload(docker_settings)
    assert docker_settings.ENABLE_CLASS is True


def test_enable_class_false(cleanup_env):
    os.environ['ENABLE_CLASS'] = 'False'
    reload(docker_settings)
    assert docker_settings.ENABLE_CLASS is False
    os.environ['ENABLE_CLASS'] = 'false'
    reload(docker_settings)
    assert docker_settings.ENABLE_CLASS is False

    
def test_cache_timeout_default(cleanup_env):
    assert 3600 == docker_settings.CACHE_DEFAULT_TIMEOUT


def test_cache_type_default(cleanup_env):
    assert 'SimpleCache' == docker_settings.CACHE_TYPE


def test_cache_memcached_servers(cleanup_env):
    os.environ['CACHE_TYPE'] = 'MemcachedCache'

    reload(docker_settings)
    assert ['memcached:11211'] == docker_settings.CACHE_MEMCACHED_SERVERS


def test_class_events_status_columns_default(cleanup_env):
    assert [('failure', 'Failure'),
            ('success', 'Success'),
            ('noop', 'Noop')] == docker_settings.CLASS_EVENTS_STATUS_COLUMNS


def test_scheduler_enabled_true(cleanup_env):
    os.environ['SCHEDULER_ENABLED'] = 'True'
    reload(docker_settings)
    assert docker_settings.SCHEDULER_ENABLED is True
    os.environ['SCHEDULER_ENABLED'] = 'true'
    reload(docker_settings)
    assert docker_settings.SCHEDULER_ENABLED is True


def test_scheduler_enabled_false(cleanup_env):
    os.environ['SCHEDULER_ENABLED'] = 'False'
    reload(docker_settings)
    assert docker_settings.SCHEDULER_ENABLED is False
    os.environ['SCHEDULER_ENABLED'] = 'false'
    reload(docker_settings)
    assert docker_settings.SCHEDULER_ENABLED is False


def test_scheduler_jobs_default(cleanup_env):   
    assert [{'func': 'puppetboard.schedulers.classes:build_async_cache',
             'id': 'do_build_async_cache_1',
             'seconds': 300,
             'trigger': 'interval'}] == docker_settings.SCHEDULER_JOBS

    
def test_scheduler_jobs_custom(cleanup_env):   
    os.environ['SCHEDULER_JOBS'] = "id,do_build_async_cache_1,func,puppetboard.schedulers.classes:build_async_cache,trigger,interval,seconds,600"
    reload(docker_settings)
    jobs = docker_settings.SCHEDULER_JOBS
    assert isinstance(jobs, list)
    assert len(jobs) == 1
    for job in jobs:
        assert isinstance(job, dict)
        assert len(job) == 4
        assert 'id' in job
        assert 'func' in job
        assert 'trigger' in job
        assert 'seconds' in job
        assert 600 == job['seconds']
