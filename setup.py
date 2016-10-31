from __future__ import with_statement
from setuptools import setup

version = '0.99.dev2'

with open("README.rst", mode='r') as fp:
    long_desc = fp.read()

setup(
    name = 'xml_browser',
    version = version,
    description = "Edit XML documents as a directory structure",
    long_description = long_desc,
    url = "https://github.com/rasguanabana/xml_browser",
    author = "Adrian Włosiak",
    author_email = "adwlosiakh@gmail.com",
    license = "MIT",
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3"
    ],
    keywords = "xml editing",
    py_modules = ['xml_browser'],
    entry_points = {'console_scripts': ['xml_browser = xml_browser:main']}
)
