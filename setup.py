import sys
import os
import codecs
import re

from setuptools import setup, find_packages
from puppetboard.version import __version__

install_requires = [
    "Flask >= 0.10.1",
    "Flask-WTF >= 0.12, <= 0.13",
    "WTForms >= 2.0, < 3.0",
    "pypuppetdb >= 0.3.2, < 0.4.0",
]

install_pinned_requires = [
    "Jinja2 >= 2.7.2",
    "MarkupSafe >= 0.19",
    "Werkzeug >= 0.11.10",
    "itsdangerous >= 0.23",
    "requests == 2.6.0",
]

tests_require = [
    "pytest >= 3.0.1",
    "pytest-pep8 >= 1.0.5",
    "pytest-cov >= 2.2.1",
    "pytest-mock >= 1.5.0",
    "mock >= 1.3.0",
    "bandit",
    "beautifulsoup4 >= 4.5.3",
]

tests_pinned_requires = [
    "pep8 >= 1.6.2",
    "coverage >= 4.0",
    "cov-core >= 1.15.0",
]
if sys.version_info < (2, 7):
    tests_pinned_requires.append("unittest2 >= 1.1.0")

docker_requires = [
    "gunicorn == 19.6.0",
]

version_parse = r'^(?P<name>[^\s<=>]+)\s*(?P<pick>[^;]*)(?P<test>(|;.*))$'


def unpin(requirements):
    for i, package in enumerate(requirements):
        requirements[i] = re.sub(version_parse, r'\g<name> \g<test>', package)


def pin(requirements):
    for i, package in enumerate(requirements):
        match = re.match(version_parse, package)
        version = re.sub(
            r'^.*((>=|==)\s*(?P<lower>[^,]+)).*$', r'== \g<lower>',
            match.group('pick'))
        requirements[i] = "%s %s%s" % (
            match.group('name'), version, match.group('test'))

with codecs.open('README.rst', encoding='utf-8') as f:
    README = f.read()

with codecs.open('CHANGELOG.rst', encoding='utf-8') as f:
    CHANGELOG = f.read()

test_deps = False
if os.environ.get('TEST_DEPS') in ('y', 'true', 'True', 't'):
    test_deps = True
deps_resolve = os.environ.get('DEPS_RESOLVE')

for arg in sys.argv[:]:
    if arg == 'publish':
        sys.argv = [sys.argv[0], 'sdist', 'upload']
        break
    elif arg == 'docker':
        sys.argv.remove(arg)
        install_requires.extend(docker_requires)
    elif arg == 'unpinned':
        sys.argv.remove(arg)
        deps_resolve = 'UNPINNED'
    elif arg == 'pinned':
        sys.argv.remove(arg)
        deps_resolve = 'PINNED'
    elif arg == 'with_test':
        sys.argv.remove(arg)
        test_deps = True

if test_deps:
    install_requires.extend(tests_require)

if deps_resolve == 'UNPINNED':
    unpin(install_requires)
elif deps_resolve == 'PINNED':
    install_requires.extend(install_pinned_requires)
    if test_deps:
        install_requires.extend(tests_pinned_requires)
    pin(install_requires)

setup(
    name='puppetboard',
    version=__version__,
    author='Corey Hammerton',
    author_email='corey.hammerton@gmail.com',
    packages=find_packages(),
    url='https://github.com/voxpupuli/puppetboard',
    license='Apache License 2.0',
    description='Web frontend for PuppetDB',
    include_package_data=True,
    long_description='\n'.join((README, CHANGELOG)),
    zip_safe=False,
    install_requires=install_requires,
    test_requires=tests_require,
    keywords="puppet puppetdb puppetboard",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Flask',
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
    ],
)
