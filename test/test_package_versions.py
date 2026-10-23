import pytest

from puppetboard.package_versions import (compare, family, parse_threshold,
                                          status)


@pytest.mark.parametrize('provider,expected', [
    ('apt', 'deb'), ('dpkg', 'deb'), ('aptitude', 'deb'),
    ('yum', 'rpm'), ('dnf', 'rpm'), ('rpm', 'rpm'), ('zypper', 'rpm'),
    ('pip3', None), ('gem', None), ('windows', None), (None, None),
])
def test_family(provider, expected):
    assert family(provider) == expected


@pytest.mark.parametrize('a,b,expected', [
    ('1.9.5', '1.10.0', -1),
    ('3.0.2-0ubuntu1.12', '3.0.2-0ubuntu1.15', -1),
    ('3.0.2-0ubuntu1.15', '3.0.2-0ubuntu1.15', 0),
    ('1.0~rc1', '1.0', -1),
    ('1.0', '1.0+b1', -1),
    ('1.0~~', '1.0~', -1),
    ('1.0', '1.0a', -1),
    ('1.0-1', '1.0', 1),
    ('3.0.2-0ubuntu1', '3.0.2', 1),
    ('1:2.0', '3.0', 1),
    ('1.01', '1.1', 0),
    ('2:1.0', '1:9.9', 1),
])
def test_compare_deb(a, b, expected):
    assert compare(a, b, 'deb') == expected
    assert compare(b, a, 'deb') == -expected


@pytest.mark.parametrize('a,b,expected', [
    ('3.0.7-27.el9', '3.0.7-28.el9', -1),
    ('1.0a', '1.0.1', -1),
    ('1.01', '1.1', 0),
    ('1.0~rc1', '1.0', -1),
    ('1.0', '1.0^git1', -1),
    ('1.0^git1', '1.0.1', -1),
    ('2.0', '10.0', -1),
    ('1.0.0', '1.0', 1),
    ('1_0', '1.0', 0),
    ('3.0.7-27.el9', '3.0.7', 0),
    ('1:3.0.7-27.el9', '0:3.0.7-28.el9', 1),
])
def test_compare_rpm(a, b, expected):
    assert compare(a, b, 'rpm') == expected
    assert compare(b, a, 'rpm') == -expected


def test_compare_huge_digit_run_does_not_raise():
    huge = '9' * 5000
    assert compare(huge, '1.0', 'deb') == 1
    assert compare(huge, '1.0', 'rpm') == 1


@pytest.mark.parametrize('installed,provider,threshold,expected', [
    # Covers AE1/AE2
    ('3.0.2-0ubuntu1.12', 'apt', '3.0.2-0ubuntu1.15', 'below'),
    ('3.0.2-0ubuntu1.15', 'apt', '3.0.2-0ubuntu1.15', 'ok'),
    ('1.9.5', 'apt', '1.10.0', 'below'),
    # threshold without epoch inherits the installed epoch
    ('1:2.0', 'apt', '3.0', 'below'),
    ('1:2.0', 'apt', '0:3.0', 'ok'),
    ('1:3.0.7-27.el9', 'yum', '3.0.7-28.el9', 'below'),
    ('1:3.0.7-28.el9', 'dnf', '3.0.7-28.el9', 'ok'),
    # Covers AE5: no verdict outside deb/rpm, or without threshold
    ('1.0', 'pip3', '2.0', 'none'),
    ('1.0', 'windows', '2.0', 'none'),
    ('1.0', 'apt', None, 'none'),
])
def test_status(installed, provider, threshold, expected):
    assert status(installed, provider, threshold) == expected


def test_status_bad_installed_version_is_no_verdict():
    assert status(None, 'apt', '1.0') == 'none'


@pytest.mark.parametrize('raw,expected', [
    (None, (None, False)),
    ('', (None, False)),
    ('   ', (None, False)),
    (' 3.0.13 ', ('3.0.13', False)),
    ('1:3.0.7-28.el9', ('1:3.0.7-28.el9', False)),
    ('1.0~rc1', ('1.0~rc1', False)),
    ('openssl-3.0.7-28.el9.x86_64', (None, True)),
    ('<3.0', (None, True)),
    ('v1.2', (None, True)),
    ('1.0 2.0', (None, True)),
    ('1' * 200, (None, True)),
])
def test_parse_threshold(raw, expected):
    assert parse_threshold(raw) == expected
