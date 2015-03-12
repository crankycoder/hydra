from setuptools import setup
from setuptools.extension import Extension
from Cython.Distutils import build_ext
from os.path import join

import os

ext_modules=[ 
        Extension("_hydra", 
            extra_compile_args=['-std=gnu99', '-O2', '-D_LARGEFILE64_SOURCE'],
            sources = [
                "src/_hydra.pyx",
                'src/mmap_writer.c',
                'src/MurmurHash3.c'],
            include_dirs = [join(os.getcwd(), 'src')],  # path to .h file(s)
            library_dirs = [join(os.getcwd(), 'src')],  # path to .a or .so file(s)
            ),
]

setup(
  name = 'Hydra',
  author='Victor Ng',
  author_email = 'crankycoder@gmail.com',
  description = 'A high performance persistent bloom filter',
  url = "http://bitbucket.org/crankycoder/Hydra",
  version='1.2',
  license = 'MIT License',
  cmdclass = {'build_ext': build_ext},
  zip_safe=False,
  package_dir = {'': 'src'},
  py_modules = ['hydra'],
  ext_modules = ext_modules,
)
