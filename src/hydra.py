import _hydra
import mmap
import struct
from os.path import exists
from os import unlink


def ReadingBloomFilter(filename, want_lock=False):
    """
    Create a read-only bloom filter with an upperbound of
    (num_elements, max_fp_prob) as a specification and using filename
    as the backing datastore.
    """
    descriptor = open('{}.desc'.format(filename), 'r')
    num_elements = int(descriptor.readline())
    max_fp_prob = float(descriptor.readline())
    ignore_case = int(descriptor.readline())

    return _hydra.BloomFilter.getFilter(
        num_elements, max_fp_prob,
        filename=filename, ignore_case=ignore_case,
        read_only=True, want_lock=want_lock)


def UpdatingBloomFilter(filename, want_lock=False):
    """
    Load an existing bloom filter in read-write mode using filename
    as the backing datastore.
    """
    descriptor = open('{}.desc'.format(filename), 'r')
    num_elements = int(descriptor.readline())
    max_fp_prob = float(descriptor.readline())
    ignore_case = int(descriptor.readline())

    return _hydra.BloomFilter.getFilter(
        num_elements, max_fp_prob,
        filename=filename, ignore_case=ignore_case,
        read_only=False, want_lock=want_lock)


def WritingBloomFilter(num_elements, max_fp_prob, filename=None,
                       ignore_case=False, want_lock=False):
    """
    Create a read/write bloom filter with an upperbound of
    (num_elements, max_fp_prob) as a specification and using filename
    as the backing datastore.
    """
    if filename:
        with open('{}.desc'.format(filename), 'w') as descriptor:
            descriptor.write("{}\n".format(num_elements))
            descriptor.write("{:0.8f}\n".format(max_fp_prob))
            descriptor.write("{:d}\n".format(ignore_case))
    return _hydra.BloomFilter.getFilter(
        num_elements, max_fp_prob,
        filename=filename, ignore_case=ignore_case,
        read_only=False, want_lock=want_lock)

# Expose the murmur hash
murmur_hash = _hydra.hash
