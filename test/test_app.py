import pytest
import tempfile

from puppetboard import app


def test_first_test():
    assert app is not None, ("%s" % reg.app)
