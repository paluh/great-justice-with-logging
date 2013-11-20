#! /usr/bin/env python
from setuptools import setup, find_packages

CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.2',
    'Topic :: Software Development :: Debuggers',
    'Topic :: Software Development :: Libraries :: Python Modules']

REQUIREMENTS = ['termcolor >= 1.0.0']

setup(name='great-justice-with-logging',
      author='Patryk Zawadzki, Tomasz Rybarczyk',
      author_email='patrys@gmail.com, paluho@gmail.com',
      description='Debug every ZIG',
      version = '1.0.3',
      packages = find_packages(),
      classifiers=CLASSIFIERS,
      install_requires=REQUIREMENTS,
      platforms=['any'],
      use_2to3 = True,
      zip_safe=True)
