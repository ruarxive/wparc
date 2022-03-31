# This is purely the result of trial and error.

import sys
import codecs

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

import wparc


class PyTest(TestCommand):
    # `$ python setup.py test' simply installs minimal requirements
    # and runs the tests with no fancy stuff like parallel execution.
    def __init__(self):
        self.test_suite = True
        self.test_args = [
            '--doctest-modules', '--verbose',
            './wparc', './tests'
        ]

    def finalize_options(self):
        TestCommand.finalize_options(self)

    def run_tests(self):
        import pytest
        sys.exit(pytest.main(self.test_args))


tests_require = [
    # Pytest needs to come last.
    # https://bitbucket.org/pypa/setuptools/issue/196/
    'pytest',
]


install_requires = [
    'lxml',
    'click',
    'pyyaml'
]


# Conditional dependencies:

# sdist
if 'bdist_wheel' not in sys.argv:
    try:
        # noinspection PyUnresolvedReferences
        import argparse
    except ImportError:
        install_requires.append('argparse>=1.2.1')


# bdist_wheel
extras_require = {
    # https://wheel.readthedocs.io/en/latest/#defining-conditional-dependencies
    'python_version == "3.0" or python_version == "3.1"': ['argparse>=1.2.1'],
}


def long_description():
    with codecs.open('README.rst', encoding='utf8') as f:
        return f.read()


setup(
    name='wparc',
    version=wparc.__version__,
    description=wparc.__doc__.strip(),
    long_description=long_description(),
    url='https://github.com/ruarxive/wparc/',
    download_url='https://github.com/ruarxive/wparc/',
    packages=find_packages(exclude=('tests', 'tests.*')),
    include_package_data=True,
    package_data={
        'wparc': ['data/*.yml'],
    },
    author=wparc.__author__,
    author_email='ivan@begtin.tech',
    license=wparc.__licence__,
    entry_points={
        'console_scripts': [
            'wparc = wparc.__main__:main',
        ],
    },
    extras_require=extras_require,
    install_requires=install_requires,
    tests_require=tests_require,
    cmdclass={'test': PyTest},
    zip_safe=False,
    keywords='backup archive wordpress',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Topic :: Software Development',
        'Topic :: System :: Networking',
        'Topic :: Terminals',
        'Topic :: Text Processing',
        'Topic :: Utilities'
    ],
)
