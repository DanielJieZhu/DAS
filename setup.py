#!/usr/bin/env python

import sys
import os
from unittest import TextTestRunner, TestLoader
from glob import glob
from os.path import splitext, basename, join as pjoin, walk
from distutils.core import setup
from distutils.cmd import Command
from distutils.command.build_ext import build_ext
from distutils.errors import CCompilerError
from distutils.errors import DistutilsPlatformError, DistutilsExecError
from distutils.core import Extension
from distutils.command.install import INSTALL_SCHEMES

sys.path.append(os.path.join(os.getcwd(), 'src/python'))
from DAS import version as das_version

required_python_version = '2.6'

if sys.platform == 'win32' and sys.version_info > (2, 6):
   # 2.6's distutils.msvc9compiler can raise an IOError when failing to
   # find the compiler
   build_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError,
                 IOError)
else:
   build_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError)

class TestCommand(Command):
    """
    Class to handle unit tests
    """
    user_options = [ ]

    def initialize_options(self):
        """Init method"""
        self._dir = os.getcwd()

    def finalize_options(self):
        """Finalize method"""
        pass

    def run(self):
        """
        Finds all the tests modules in test/, and runs them.
        """
        testfiles = [ ]
        for t in glob(pjoin(self._dir, 'test', '*_t.py')):
            if not t.endswith('__init__.py'):
                testfiles.append('.'.join(
                    ['test', splitext(basename(t))[0]])
                )
        tests = TestLoader().loadTestsFromNames(testfiles)
        t = TextTestRunner(verbosity = 2)
        t.run(tests)

class CleanCommand(Command):
    """
    Class which clean-up all pyc files
    """
    user_options = [ ]

    def initialize_options(self):
        """Init method"""
        self._clean_me = [ ]
        for root, dirs, files in os.walk('.'):
            for f in files:
                if f.endswith('.pyc'):
                    self._clean_me.append(pjoin(root, f))

    def finalize_options(self):
        """Finalize method"""
        pass

    def run(self):
        """Run method"""
        for clean_me in self._clean_me:
            try:
                os.unlink(clean_me)
            except:
                pass

class BuildExtCommand(build_ext):
    """
    Allow C extension building to fail.
    The C extension speeds up DAS, but is not essential.
    """

    warning_message = """
**************************************************************
WARNING: %s could not
be compiled. No C extensions are essential for DAS to run,
although they do result in significant speed improvements.

%s
**************************************************************
"""

    def run(self):
        try:
            build_ext.run(self)
        except DistutilsPlatformError, e:
            print e
            print self.warning_message % ("Extension modules",
                                          "There was an issue with your "
                                          "platform configuration - see above.")

    def build_extension(self, ext):
        try:
            build_ext.build_extension(self, ext)
        except build_errors:
            print self.warning_message % ("The %s extension module" % ext.name,
                                          "Above is the ouput showing how "
                                          "the compilation failed.")

def dirwalk(relativedir):
    """
    Walk a directory tree and look-up for __init__.py files.
    If found yield those dirs. Code based on
    http://code.activestate.com/recipes/105873-walk-a-directory-tree-using-a-generator/
    """
    dir = os.path.join(os.getcwd(), relativedir)
    for fname in os.listdir(dir):
        fullpath = os.path.join(dir, fname)
        if  os.path.isdir(fullpath) and not os.path.islink(fullpath):
            for subdir in dirwalk(fullpath):  # recurse into subdir
                yield subdir
        else:
            initdir, initfile = os.path.split(fullpath)
            if  initfile == '__init__.py':
                yield initdir

def find_packages(relativedir):
    packages = [] 
    for dir in dirwalk(relativedir):
        package = dir.replace(os.getcwd() + '/', '')
        package = package.replace(relativedir + '/', '')
        package = package.replace('/', '.')
        packages.append(package)
    return packages

def datafiles(dir):
    """Return list of data files in provided relative dir"""
    files = []
    for dirname, dirnames, filenames in os.walk(dir):
        for subdirname in dirnames:
            files.append(os.path.join(dirname, subdirname))
        for filename in filenames:
            if  filename[-1] == '~':
                continue
            files.append(os.path.join(dirname, filename))
    return files
#    return [os.path.join(dir, f) for f in os.listdir(dir)]
    
version      = das_version
name         = "DAS"
description  = "CMS Data Aggregation System"
readme       ="""
DAS stands for Data Aggregation System
<https://twiki.cern.ch/twiki/bin/viewauth/CMS/DMWMDataAggregationService>
"""
author       = "Valentin Kuznetsov",
author_email = "vkuznet@gmail.com",
scriptfiles  = filter(os.path.isfile, ['etc/das.cfg'])
url          = "https://twiki.cern.ch/twiki/bin/viewauth/CMS/DMWMDataAggregationService",
keywords     = ["DAS", "Aggregation", "Meta-data"]
package_dir  = {'DAS': 'src/python/DAS'}
packages     = find_packages('src/python')
data_files   = [
                ('DAS/etc', ['etc/das.cfg']),
                ('DAS/test', datafiles('test')),
                ('DAS/services/maps', datafiles('src/python/DAS/services/maps')),
                ('DAS/web/js', datafiles('src/js')),
                ('DAS/web/css', datafiles('src/css')),
                ('DAS/web/images', datafiles('src/images')),
                ('DAS/web/templates', datafiles('src/templates')),
               ]
license      = "CMS experiment software"
classifiers  = [
    "Development Status :: 3 - Production/Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: CMS/CERN Software License",
    "Operating System :: MacOS :: MacOS X",
    "Operating System :: Microsoft :: Windows",
    "Operating System :: POSIX",
    "Programming Language :: Python",
    "Topic :: Database"
]

def main():
    if sys.version < required_python_version:
        s = "I'm sorry, but %s %s requires Python %s or later."
        print s % (name, version, required_python_version)
        sys.exit(1)

    # set default location for "data_files" to
    # platform specific "site-packages" location
    for scheme in INSTALL_SCHEMES.values():
        scheme['data'] = scheme['purelib']

    dist = setup(
        name                 = name,
        version              = version,
        description          = description,
        long_description     = readme,
        keywords             = keywords,
        packages             = packages,
        package_dir          = package_dir,
        data_files           = data_files,
        scripts              = datafiles('bin'),
        requires             = ['python (>=2.6)', 'pymongo (>=1.6)', 'ply (>=3.3)',
                                'sphinx (>=1.0.4)', 'cherrypy (>=3.1.2)',
                                'Cheetah (>=2.4)', 'yaml (>=3.09)'],
        ext_modules          = [Extension('DAS.extensions.das_speed_utils',
                               include_dirs=['extensions'],
                               sources=['src/python/DAS/extensions/dict_handler.c'])],
        classifiers          = classifiers,
        cmdclass             = {'build_ext': BuildExtCommand,
                                'test': TestCommand, 
                                'clean': CleanCommand},
        author               = author,
        author_email         = author_email,
        url                  = url,
        license              = license,
    )

if __name__ == "__main__":
    main()

