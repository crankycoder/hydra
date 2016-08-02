[![Build Status](https://travis-ci.org/crankycoder/hydra.svg?branch=master)](https://travis-ci.org/crankycoder/hydra)

Hydra: The Python Bloom Filter.

Compile with Cython 0.24 or higher.

---

Hydra is a high performance bloom filter.  It's basically a port of
the Cassandra bloom filter with some fun Cython hackery.

1) It's persistent using memory mapped io.  On Linux, the mmap uses
the MAP_POPULATE flag so the entire file is loaded into kernel space
virtual memory.  In other words - fast.

2) The hash function uses the MurmurHash3 algorithm, so it should be
fast and have excellent key distribution and avalanche properties.

3) The filter exports a set-like interface. Use .add(..), .contains()
or use the "in" operator.

4) Tests. OMG what is wrong with people with no tests?

The filter supports periodic forced synchronization to disk using
fdatasync(), or you can just let the deallocator flush everything to
disk when your filter goes out of scope, or your process terminates.

Hydras are snakes with multiple heads.  They're also bad dudes with
snake logos on their chest who regularly try to beat on Nick Fury.
Now it's a bloom filter.  

Mostly, I couldn't bear to make this yet another PySomeLibraryName
library.


Build, install a dev build and test:

    $ pip install -r requirements.txt
    $ cythonize src/_hydra.pyx
    $ python setup.py develop
    $ python setup.py test
