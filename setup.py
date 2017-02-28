import sys
import os
import codecs
import re

UNPINNED = os.getenv('UNPINNED', None)
VERSION_RE = r'^(?P<name>[^\s<=>]+)\s*(?P<pick>[^;]*)(?P<test>(|;.*))$'


from setuptools import setup, find_packages
from puppetboard.version import __version__

with codecs.open('README.rst', encoding='utf-8') as f:
    README = f.read()

with codecs.open('CHANGELOG.rst', encoding='utf-8') as f:
    CHANGELOG = f.read()

def fuzzy(depend):
    if UNPINNED is not None:
        match = re.match(VERSION_RE, depend)
        return match.group('name')
    else:
        return depend.replace('==', '>=')

requirements = None
with open('requirements.txt', 'r') as f:
    requirements = [fuzzy(line.rstrip())
                    for line in f.readlines() if not line.startswith('-')]

requirements_test = None
with open('requirements-test.txt', 'r') as f:
    requirements_test = [line.rstrip() for line in f.readlines()
                         if not line.startswith('-')]

requirements = [pypi for pypi in reversed(requirements)]
print requirements


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
    setup_requires=['pytest-runner'],
    install_requires=requirements,
    tests_require=requirements_test,
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
