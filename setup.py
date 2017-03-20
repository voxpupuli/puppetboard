import sys
import os
import codecs

from setuptools import setup, find_packages


if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

VERSION = "0.2.2"

with codecs.open('README.rst', encoding='utf-8') as f:
    README = f.read()

with codecs.open('CHANGELOG.rst', encoding='utf-8') as f:
    CHANGELOG = f.read()

setup(
    name='puppetboard',
    version=VERSION,
    author='Corey Hammerton',
    author_email='corey.hammerton@gmail.com',
    packages=find_packages(),
    url='https://github.com/voxpupuli/puppetboard',
    license='Apache License 2.0',
    description='Web frontend for PuppetDB',
    include_package_data=True,
    long_description='\n'.join((README, CHANGELOG)),
    zip_safe=False,
    install_requires=[
        "Flask >= 0.10.1",
        "Flask-WTF >= 0.12, <= 0.13",
        "WTForms >= 2.0, < 3.0",
        "Werkzeug >=0.7, <= 0.11.5",
        "pypuppetdb >= 0.3.0, < 0.4.0",
    ],
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
