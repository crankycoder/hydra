from setuptools import setup
from setuptools.extension import Extension
from os.path import join

import os

__version__ = '2.5'

ext_modules = [Extension("_hydra",
                         extra_compile_args=['-std=gnu99',
                                             '-O2',
                                             '-D_LARGEFILE64_SOURCE'],
                         sources=["src/_hydra.c",
                                  'src/mmap_writer.c',
                                  'src/MurmurHash3.c'],

                         # path to .h file(s)
                         include_dirs=[join(os.getcwd(), 'src')],

                         # path to .a or .so file(s)
                         library_dirs=[join(os.getcwd(), 'src')])]

setup(name='Hydra',
      author='Victor Ng',
      author_email='crankycoder@gmail.com',
      description='A high performance persistent bloom filter',
      url="http://github.com/crankycoder/Hydra",
      version=__version__,
      license='MIT License',
      zip_safe=False,
      package_dir={'': 'src'},
      py_modules=['hydra'],
      ext_modules=ext_modules,
      test_suite='nose.collector',
      classifiers=[
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: Implementation :: CPython',
      ],
)
