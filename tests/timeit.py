"""
This is a speed profiler for insertion and lookup
"""
import cProfile
from hydra import WritingBloomFilter
from helpers import KeyGenerator

keygen = KeyGenerator()
input_keys = [keygen.random_string() for i in xrange(20000)]
other_keys = [keygen.random_string() for i in xrange(20000)]

ELEMENTS = 10000000
MAX_FAILURE_RATE = 0.1
bf = WritingBloomFilter(ELEMENTS, MAX_FAILURE_RATE)


def test_one():
    for key in input_keys:
        bf.add(key)

    for key in other_keys:
        bf.isPresent(key)

cProfile.run('test_one()')
