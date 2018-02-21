"""
Flask-APIExceptions
~~~~~~~~~~~~~~~~~~~

Providing HTTP error responses in the form of Python exceptions that can
be serialized as response objects.

"""

import os

from setuptools import setup

with open('README.rst') as file:
    long_description = file.read()

module_path = os.path.join(os.path.dirname(__file__), 'flask_apiexceptions.py')
with open(module_path) as module:
    for line in module:
        if line.startswith('__version_info__'):
            version_line = line
            break

__version__ = '.'.join(eval(version_line.split('__version_info__ = ')[-1]))

url_base = 'https://github.com/jperras/Flask-ApiExceptions'

setup(
    name='Flask-ApiExceptions',
    version=__version__,
    author='Joel Perras',
    author_email='joel@nerderati.com',
    description='Python exceptions serializable to Flask HTTP responses.',
    url=url_base,
    download_url='{}/archive/{}.tar.gz'.format(url_base, __version__),
    long_description=long_description,
    py_modules=['flask_apiexceptions'],
    license='MIT',
    platforms='any',
    install_requires=['Flask>=0.10'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    keywords=['flask', 'json', 'exceptions', 'api'],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)
