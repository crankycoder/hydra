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


class Bitmap(object):
    """
    This was a pure python mmap-io class that was being used to
    persist data before the whole thing was moved into Cython.  Here
    for mainly historical reasons.
    """
    def __init__(self, filename, bitsize, start_fresh=True):
        self._filename = filename
        if start_fresh:
            if exists(filename):
                unlink(filename)
        self._file = file(filename, 'wb+')

        self._bitsize = bitsize

        # Pad out the last couple bits to a full byte
        self._size = self._bitsize / 8 + 1
        self._file.seek(self._size)
        self._file.write(struct.pack('B', 0))
        self._file.seek(0)
        self._mfile = mmap.mmap(self._file.fileno(), self._size)

    def __len__(self):
        return self._bitsize

    def __setitem__(self, k, v):
        if k >= self._bitsize:
            raise RuntimeError(
                "OutOfBounds! Max bit is : {}, requested: {}".format(
                    self._bitsize, k))
        byte_offset = k / 8
        old_bitmask = struct.unpack('B', self._mfile[byte_offset])[0]
        if v:
            new_bitmask = old_bitmask | 2**(k % 8)
        else:
            new_bitmask = old_bitmask ^ 2**(k % 8)
        self._mfile[byte_offset] = struct.pack('B', new_bitmask)

    def __getitem__(self, k):
        byte_offset = k / 8
        old_bitmask = struct.unpack('B', self._mfile[byte_offset])[0]
        return bool(old_bitmask & 2**(k % 8))
