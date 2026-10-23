"""Debian (dpkg) and RPM version comparison for the Packages view.

Ports of dpkg's verrevcmp (lib/dpkg/version.c) and rpm's rpmvercmp
(rpmio/rpmvercmp.c). Digit runs are compared as strings (length, then
lexically) so that agent-reported versions can never make int() blow up.
"""
import logging
import re

log = logging.getLogger(__name__)

# ponytail: provider names assumed from Puppet's package providers, extend
# when real PuppetDB data shows others (unknown providers get no verdict).
FAMILIES = {
    'apt': 'deb', 'aptitude': 'deb', 'dpkg': 'deb',
    'yum': 'rpm', 'dnf': 'rpm', 'rpm': 'rpm', 'zypper': 'rpm', 'up2date': 'rpm',
}
THRESHOLD_MAX_LENGTH = 128
THRESHOLD_RE = re.compile(r'^([0-9]+:)?[0-9][A-Za-z0-9.+~^_-]*$')
DIGITS = '0123456789'
# Row statuses, from the most to the least severe
STATUSES = ('below', 'none', 'ok')


def family(provider):
    return FAMILIES.get(provider)


def parse_threshold(raw):
    """Returns (threshold, invalid). An empty value means no threshold."""
    value = (raw or '').strip()
    if not value:
        return None, False
    if len(value) > THRESHOLD_MAX_LENGTH or not THRESHOLD_RE.match(value):
        return None, True
    return value, False


def _cmp(a, b):
    return (a > b) - (a < b)


def _isdigit(c):
    return c != '' and c in DIGITS


def _isalpha(c):
    return c.isascii() and c.isalpha()


def _digit_run(s, i):
    start = i
    while i < len(s) and _isdigit(s[i]):
        i += 1
    return s[start:i].lstrip('0'), i


def _cmp_numbers(a, b):
    return _cmp(len(a), len(b)) or _cmp(a, b)


def _deb_order(c):
    if c == '' or _isdigit(c):
        return 0
    if _isalpha(c):
        return ord(c)
    if c == '~':
        return -1
    return ord(c) + 256


def _verrevcmp(a, b):
    i = j = 0
    while i < len(a) or j < len(b):
        while ((i < len(a) and not _isdigit(a[i]))
               or (j < len(b) and not _isdigit(b[j]))):
            ac = _deb_order(a[i:i + 1])
            bc = _deb_order(b[j:j + 1])
            if ac != bc:
                return _cmp(ac, bc)
            i += 1
            j += 1
        da, i = _digit_run(a, i)
        db, j = _digit_run(b, j)
        result = _cmp_numbers(da, db)
        if result:
            return result
    return 0


def _rpmvercmp(a, b):
    if a == b:
        return 0
    i = j = 0
    while i < len(a) or j < len(b):
        while i < len(a) and not (a[i].isascii() and a[i].isalnum()) and a[i] not in '~^':
            i += 1
        while j < len(b) and not (b[j].isascii() and b[j].isalnum()) and b[j] not in '~^':
            j += 1
        ca, cb = a[i:i + 1], b[j:j + 1]

        # tilde sorts before everything else
        if ca == '~' or cb == '~':
            if ca != '~':
                return 1
            if cb != '~':
                return -1
            i += 1
            j += 1
            continue

        # caret sorts after the end of a version but before anything else
        if ca == '^' or cb == '^':
            if not ca:
                return -1
            if not cb:
                return 1
            if ca != '^':
                return 1
            if cb != '^':
                return -1
            i += 1
            j += 1
            continue

        if not (ca and cb):
            break

        start_j = j
        if _isdigit(ca):
            sa, i = _digit_run(a, i)
            sb, j = _digit_run(b, j)
            if j == start_j:
                return 1  # numeric segments are newer than alpha ones
            result = _cmp_numbers(sa, sb)
        else:
            start_i = i
            while i < len(a) and _isalpha(a[i]):
                i += 1
            while j < len(b) and _isalpha(b[j]):
                j += 1
            if j == start_j:
                return -1
            result = _cmp(a[start_i:i], b[start_j:j])
        if result:
            return result

    a_left, b_left = i < len(a), j < len(b)
    if not a_left and not b_left:
        return 0
    return 1 if a_left else -1


def _split_epoch(version):
    epoch, sep, rest = version.partition(':')
    if sep and epoch.isascii() and epoch.isdigit():
        return epoch.lstrip('0'), rest
    return None, version


def compare(a, b, fam):
    """Compares two versions of the 'deb' or 'rpm' family: -1, 0 or 1."""
    epoch_a, rest_a = _split_epoch(a)
    epoch_b, rest_b = _split_epoch(b)
    result = _cmp_numbers(epoch_a or '', epoch_b or '')
    if result:
        return result
    version_a, sep_a, release_a = rest_a.rpartition('-')
    version_b, sep_b, release_b = rest_b.rpartition('-')
    if not sep_a:
        version_a = release_a
        release_a = None
    if not sep_b:
        version_b = release_b
        release_b = None

    if fam == 'deb':
        return (_verrevcmp(version_a, version_b)
                or _verrevcmp(release_a or '', release_b or ''))
    result = _rpmvercmp(version_a, version_b)
    # like rpm, the release is only compared when both sides have one
    if result or not (release_a and release_b):
        return result
    return _rpmvercmp(release_a, release_b)


def status(installed, provider, threshold):
    """Returns 'below', 'ok' or 'none' (no verdict) for an installed version.

    A threshold without epoch takes the epoch of the installed version, so
    that a version copied from a security advisory compares as expected.
    """
    fam = family(provider)
    if not (fam and threshold and installed):
        return 'none'
    try:
        epoch, _ = _split_epoch(installed)
        if epoch and _split_epoch(threshold)[0] is None:
            threshold = f'{epoch}:{threshold}'
        return 'below' if compare(installed, threshold, fam) < 0 else 'ok'
    except Exception:  # never let one odd agent-reported version break the page
        log.warning('Cannot compare version %r with threshold %r', installed, threshold,
                    exc_info=True)
        return 'none'
