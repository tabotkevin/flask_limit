"""
Flask_Limit
--------------

An extension that provides rate limiting for Flask routes.
"""
import re
from setuptools import setup

with open('flask_limit/__init__.py', 'r') as f:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        f.read(), re.MULTILINE).group(1)

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='Flask_Limit',
    version=version,
    url='https://github.com/tabotkevin/flask_limit',
    license='MIT',
    author='Tabot Kevin',
    author_email='tabot.kevin@gmail.com',
    description='An extension that provides rate limiting for Flask routes.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=['flask_limit'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'Flask'
    ],
    test_suite="tests",
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
