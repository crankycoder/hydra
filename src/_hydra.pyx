cimport cython
import operator
import os
import sys
import tempfile

cdef extern from "ctype.h" nogil:
    cdef int tolower (int c)

cdef extern from "stdlib.h" nogil:
    long long int llabs(long long int j)


cdef extern from "stdio.h" nogil:
    ctypedef struct FILE
    FILE *fopen(char *path, char *mode)
    int fclose(FILE *strea)
    cdef char* fgets (char *buffer, int fd, FILE *stream)

cdef extern from "mmap_writer.h" nogil:
    cdef char* map_file_ro(int fd, size_t filesize, int want_lock) except NULL
    cdef char* map_file_rw(int fd, size_t filesize, int want_lock) except NULL
    cdef int open_mmap_file_ro(char* filepath) except -1
    cdef int open_mmap_file_rw(char* filename, size_t bytesize) except -1
    cdef void bulkload_file(char* buffer, char* filename)
    cdef int close_file(int fd) except -1
    cdef int flush_to_disk(int fd) except -1
    cdef void turn_bits_on(char *map, size_t index, char bitmask)
    cdef int unmap_file(char* map, size_t filesize) except -1

cdef extern from "MurmurHash3.h" nogil:
    void MurmurHash3_x64_128 (void * key, int len, unsigned int seed, void * out)

def hash(key, int seed=0):
    """ This function hashes a string using the Murmur3 hash algorithm"""
    cdef long result[2]
    if isinstance(key, unicode):
        key = key.encode('utf8')
    MurmurHash3_x64_128(<char*>key, len(key), seed, result)
    return long(result[0]) << 64 | (long(result[1]) & 0xFFFFFFFFFFFFFFFF)

cdef class MMapBitField:
    cdef char* _filename
    cdef int _fd
    cdef long _bitsize
    cdef long _bytesize
    cdef char* _buffer
    cdef int _read_only
    cdef int _fdatasync_on_close

    def __cinit__(self, filename, long bitsize, int read_only, int want_lock=False, int fdatasync_on_close=True):
        if isinstance(filename, unicode):
            filename = filename.encode('utf8')
        self._filename = filename
        self._bitsize = bitsize
        self._bytesize = (bitsize / 8) + 2
        self._read_only = read_only
        self._fdatasync_on_close = fdatasync_on_close

        # Now setup the file and mmap
        if read_only:
            self.open_ro_buffer(want_lock)
        else:
            self.open_rw_buffer(want_lock)

    cdef void open_rw_buffer(self, want_lock=False):
        self._fd = open_mmap_file_rw(self._filename, self._bytesize)
        self._buffer = map_file_rw(self._fd, self._bytesize, want_lock)

    cdef void open_ro_buffer(self, want_lock=False):
        self._fd = open_mmap_file_ro(self._filename)
        self._buffer = map_file_ro(self._fd, self._bytesize, want_lock)
        
    def __dealloc__(self):
        self.close()

    def close(self):
        if self._fd >= 0 and self._buffer:
            if not self._read_only and self._fdatasync_on_close:
                flush_to_disk(self._fd)
            unmap_file(self._buffer, self._bytesize)
            close_file(self._fd)
            self._fd = -1
            self._buffer = NULL

    def fdatasync(self):
        """ Flush everything to disk """
        if self._fd < 0 or not self._buffer:
            raise ValueError('I/O operation on closed file')

        if self._read_only:
            raise ValueError('bit field is read only')

        flush_to_disk(self._fd)

    def __setitem__(self, size_t key, int value):
        cdef size_t byte_offset = key / 8
        cdef char bitmask
        cdef char bitval

        if self._fd < 0 or not self._buffer:
            raise ValueError('I/O operation on closed file')

        if self._read_only:
            raise ValueError('bit field is read only')

        bitmask = 2 ** (key % 8)
        if value:
            bitval = self._buffer[byte_offset] | bitmask
            self._buffer[byte_offset] = bitval
        else:
            self._buffer[byte_offset] &= ~bitmask

    def __getitem__(self, size_t key):
        cdef size_t byte_offset = key / 8

        if self._fd < 0 or not self._buffer:
            raise ValueError('I/O operation on closed file')

        cdef char old_bitmask = self._buffer[byte_offset]
        return <int> (old_bitmask & <char> (2 ** (key % 8)))

    def __iter__(self):
        if self._fd < 0 or not self._buffer:
            raise ValueError('I/O operation on closed file')

        return MMapIter(self)

    def __len__(self):
        if self._fd < 0 or not self._buffer:
            raise ValueError('I/O operation on closed file')

        return self._bitsize

cdef class MMapIter:
    cdef size_t _idx
    cdef MMapBitField  _bitfield
    def __cinit__(self, bitfield):
        self._bitfield = bitfield
        self._idx = 0

    def __next__(self):
        cdef int result
        if self._idx < len(self._bitfield):
            result = self._bitfield[self._idx]
            self._idx +=1
            return result
        raise StopIteration


class UnsupportedOperationException(Exception): pass

class BloomSpecification:
    """
    A wrapper class that holds two key parameters for a Bloom Filter: the
    number of hash functions used, and the number of buckets per element used.
    """

    def __init__(self, k, bucketsPerElement):
        self.K = k
        self.bucketsPerElement = bucketsPerElement

    def __eq__(self, other):
        c1 = getattr(other, 'K', None) == self.K
        c2 = getattr(other, 'bucketsPerElement', None) == self.bucketsPerElement
        return c1 and c2

cdef class BloomCalculations:
    """
    This calculation class is ported straight from Cassandra.
    """
    minBuckets = 2
    minK = 1

    PROBS = [
            [1.0], #  dummy row representing 0 buckets per element
            [1.0, 1.0], #  dummy row representing 1 buckets per element
            [1.0, 0.393,  0.400],
            [1.0, 0.283,  0.237,   0.253],
            [1.0, 0.221,  0.155,   0.147,   0.160],
            [1.0, 0.181,  0.109,   0.092,   0.092,   0.101], # 5
            [1.0, 0.154,  0.0804,  0.0609,  0.0561,  0.0578,   0.0638],
            [1.0, 0.133,  0.0618,  0.0423,  0.0359,  0.0347,   0.0364],
            [1.0, 0.118,  0.0489,  0.0306,  0.024,   0.0217,   0.0216,   0.0229],
            [1.0, 0.105,  0.0397,  0.0228,  0.0166,  0.0141,   0.0133,   0.0135,   0.0145],
            [1.0, 0.0952, 0.0329,  0.0174,  0.0118,  0.00943,  0.00844,  0.00819,  0.00846], # 10
            [1.0, 0.0869, 0.0276,  0.0136,  0.00864, 0.0065,   0.00552,  0.00513,  0.00509],
            [1.0, 0.08,   0.0236,  0.0108,  0.00646, 0.00459,  0.00371,  0.00329,  0.00314],
            [1.0, 0.074,  0.0203,  0.00875, 0.00492, 0.00332,  0.00255,  0.00217,  0.00199,  0.00194],
            [1.0, 0.0689, 0.0177,  0.00718, 0.00381, 0.00244,  0.00179,  0.00146,  0.00129,  0.00121,  0.0012],
            [1.0, 0.0645, 0.0156,  0.00596, 0.003,   0.00183,  0.00128,  0.001,    0.000852, 0.000775, 0.000744], # 15
            [1.0, 0.0606, 0.0138,  0.005,   0.00239, 0.00139,  0.000935, 0.000702, 0.000574, 0.000505, 0.00047,  0.000459],
            [1.0, 0.0571, 0.0123,  0.00423, 0.00193, 0.00107,  0.000692, 0.000499, 0.000394, 0.000335, 0.000302, 0.000287, 0.000284],
            [1.0, 0.054,  0.0111,  0.00362, 0.00158, 0.000839, 0.000519, 0.00036,  0.000275, 0.000226, 0.000198, 0.000183, 0.000176],
            [1.0, 0.0513, 0.00998, 0.00312, 0.0013,  0.000663, 0.000394, 0.000264, 0.000194, 0.000155, 0.000132, 0.000118, 0.000111, 0.000109],
            [1.0, 0.0488, 0.00906, 0.0027,  0.00108, 0.00053,  0.000303, 0.000196, 0.00014,  0.000108, 8.89e-05, 7.77e-05, 7.12e-05, 6.79e-05, 6.71e-05] # 20
            ]

    optKPerBuckets = [max(1, min(enumerate(probs), key=operator.itemgetter(1))[0]) for probs in PROBS]

    @classmethod
    def computeBloomSpec1(cls, bucketsPerElement):
        """
        Given the number of buckets that can be used per element, return a
        specification that minimizes the false positive rate.

        @param bucketsPerElement The number of buckets per element for the filter.
        @return A spec that minimizes the false positive rate.
        """
        assert bucketsPerElement >= 1
        assert bucketsPerElement <= len(BloomCalculations.PROBS) - 1
        return BloomSpecification(cls.optKPerBuckets[bucketsPerElement], bucketsPerElement)


    @classmethod
    def computeBloomSpec2(cls, maxBucketsPerElement, maxFalsePosProb):
        """
        Given a maximum tolerable false positive probability, compute a Bloom
        specification which will give less than the specified false positive rate,
        but minimize the number of buckets per element and the number of hash
        functions used.  Because bandwidth (and therefore total bitvector size)
        is considered more expensive than computing power, preference is given
        to minimizing buckets per element rather than number of hash functions.

        @param maxBucketsPerElement The maximum number of buckets available for the filter.
        @param maxFalsePosProb The maximum tolerable false positive rate.
        @return A Bloom Specification which would result in a false positive rate
        less than specified by the function call
        @throws UnsupportedOperationException if a filter satisfying the parameters cannot be met
        """
        assert maxBucketsPerElement >= 1
        assert maxBucketsPerElement <= len(BloomCalculations.PROBS) - 1
        maxK = len(BloomCalculations.PROBS[maxBucketsPerElement]) - 1

        # Handle the trivial cases
        if maxFalsePosProb >= BloomCalculations.PROBS[cls.minBuckets][cls.minK]:
            return BloomSpecification(2, cls.optKPerBuckets[2])

        if maxFalsePosProb < BloomCalculations.PROBS[maxBucketsPerElement][maxK]:
            msg = "Unable to satisfy %s with %s buckets per element"
            raise  UnsupportedOperationException(msg % (maxFalsePosProb, maxBucketsPerElement))

        # First find the minimal required number of buckets:
        bucketsPerElement = 2
        K = cls.optKPerBuckets[2]
        while(BloomCalculations.PROBS[bucketsPerElement][K] > maxFalsePosProb):
            bucketsPerElement += 1
            K = cls.optKPerBuckets[bucketsPerElement]
        # Now that the number of buckets is sufficient, see if we can relax K
        # without losing too much precision.
        while BloomCalculations.PROBS[bucketsPerElement][K - 1] <= maxFalsePosProb:
            K -= 1

        return BloomSpecification(K, bucketsPerElement)

cdef class BloomFilter:
    EXCESS = 20
    cdef unsigned int _hashCount
    cdef MMapBitField _bitmap
    cdef int _ignore_case
    cdef object _tempfile

    def __cinit__(self, unsigned int hashes, MMapBitField bitmap, int ignore_case):
        cdef int i

        self._hashCount = hashes
        self._bitmap = bitmap
        self._ignore_case = ignore_case

    def __enter__(self):
        return self

    def __exit__(self, *excinfo):
        self.close()
        return None

    def close(self):
        self._bitmap.close()

    def fdatasync(self):
        """ Flush everything to disk """
        self._bitmap.fdatasync()

    def filename(self):
        """
        Filename of the MMAP file
        """
        return self._bitmap._filename

    @classmethod
    def _maxBucketsPerElement(cls, numElements):
        numElements = max(1, numElements)
        v = (sys.maxsize - cls.EXCESS) / float(numElements)
        if v < 1.0:
            msg = "Cannot compute probabilities for %s elements."
            raise UnsupportedOperationException, msg % numElements
        return min(len(BloomCalculations.PROBS) - 1, int(v))

    @classmethod
    def _bucketsFor(cls, numElements, bucketsPer, filename, read_only, want_lock=False, fdatasync_on_close=True):
        numBits = numElements * bucketsPer + cls.EXCESS
        bf_size = min(sys.maxsize, numBits)
        return MMapBitField(filename, bf_size, read_only,
                            want_lock=want_lock,
                            fdatasync_on_close=fdatasync_on_close)

    @classmethod
    def getFilter(cls, numElements, maxFalsePosProbability, **kwargs):
        """
        Create a bloom filter.

        numElements and maxFalsePosProbability are taken to form a
        speciification for the Bloom Filter.  The filter is designed
        to hold a maximum of numElements entries and will have an
        upper bound false positive error rate of
        maxFalsePosProbability.

        Optional **kwargs:

        filename: The filepath of the mmap io file.  If set to None - a file
                  will be created in temporary storage. Default: None

        ignore_case: All strings will be forced into lower case for
                     both add and search functions. Default: False

        read_only: The file will be opened in read-only mode and the
                   memory map will be setup in read only mode. Default False

        """
        filename = kwargs.get('filename', None)
        ignore_case = kwargs.get('ignore_case', 0)
        read_only = kwargs.get('read_only', 0)
        want_lock = kwargs.get('want_lock', False)
        fdatasync_on_close = kwargs.get('fdatasync_on_close', True)

        for k in ['filename', 'ignore_case', 'read_only', 'want_lock', 'fdatasync_on_close']:
            if kwargs.has_key(k):
                del kwargs[k]
        if kwargs:
            raise RuntimeError, "Unexpected kwargs: %s" % str(kwargs)

        if not filename:
            fileobj = tempfile.NamedTemporaryFile(delete=True)
            fileobj.file.close()
            filename = fileobj.name

        assert 0 < maxFalsePosProbability <= 1.0, "Invalid probability"
        bucketsPerElement = cls._maxBucketsPerElement(numElements)
        spec = BloomCalculations.computeBloomSpec2(bucketsPerElement, maxFalsePosProbability)
        bitmap = cls._bucketsFor(numElements, spec.bucketsPerElement, filename, read_only, want_lock=want_lock, fdatasync_on_close=fdatasync_on_close)
        bf = BloomFilter(spec.K, bitmap, ignore_case)
        if not filename:
            bf._tempfile = fileobj
        return bf

    def __setitem__(self, key, int ignored):
        self.add(key)

    def __getitem__(self, key):
        return int(self.contains(key))

    def __contains__(self, ustring):
        return self.contains(ustring)

    @cython.boundscheck(False)
    def add(self, ustring):
        """ Add a key into the filter.  Just like a set.  """
        cdef unsigned long long i
        cdef unsigned long long _bucket_indexes[1000]

        if isinstance(ustring, unicode):
            key = ustring.encode('utf8')
        else:
            key = ustring

        if self._ignore_case:
            c_lcase(key);

        self._get_hash_buckets(key, _bucket_indexes, self._hashCount, self.buckets())
        for i in range(self._hashCount):
            self._bitmap[_bucket_indexes[i]] = 1

    @cython.boundscheck(False)
    def contains(self, ustring):
        """ Check if a key is in the bloom filter.  May return a false positive. """
        cdef unsigned long long _bucket_indexes[1000]
        cdef unsigned long long i

        if isinstance(ustring, unicode):
            key = ustring.encode('utf8')
        else:
            key = ustring

        if self._ignore_case:
            c_lcase(key);
        self._get_hash_buckets(key, _bucket_indexes, self._hashCount, self.buckets())
        for i in range(self._hashCount):
            if not self._bitmap[_bucket_indexes[i]]:
                return False
        return True

    def buckets(self):
        """ Return the number of total buckets (bits) in the bloom filter """
        return len(self._bitmap)

    def getHashBuckets(self, key, unsigned int hashCount, unsigned long long max):
        """ This method is just available for test purposes.  Not actually useful for normal users. """
        cdef unsigned long long _bucket_indexes[1000]

        self._get_hash_buckets(key, _bucket_indexes, hashCount, max)
        result = []
        for i in range(hashCount):
            result.append(_bucket_indexes[i])
        return result

    @cython.boundscheck(False)
    cdef void _get_hash_buckets(self, key, unsigned long long * _bucket_indexes, unsigned int hashCount, unsigned long max):
        """
        Murmur is faster than an SHA-based approach and provides as-good collision
        resistance.  The combinatorial generation approach described in
        http://www.eecs.harvard.edu/~kirsch/pubs/bbbf/esa06.pdf
        does prove to work in actual tests, and is obviously faster
        than performing further iterations of murmur.
        """
        cdef unsigned long result[2]
        cdef unsigned long hash1, hash2
        cdef unsigned long i

        if isinstance(key, unicode):
            key = key.encode('utf8')

        MurmurHash3_x64_128(<char*>key, len(key), 0, result)
        hash1 = result[0]
        MurmurHash3_x64_128(<char*>key, len(key), result[1] & 0xFFFFFFFF, result)
        hash2 = result[0]

        for i in range(hashCount):
            _bucket_indexes[i] = llabs((hash1 + i * hash2) % max)

    cdef void _strip_newline(self, char *buffer, unsigned int size):
        """
        Strip newline by overwriting with a null
        """
        cdef unsigned int i
        for i in range(size):
            if buffer[i] == '\n':
                buffer[i] = '\x00'
                return

    def bulkload_text(self, char* filename):
        cdef FILE* file_in = fopen( filename, "r")
        cdef char line[128]
        if file_in:
            while fgets(line, 128, file_in):
                self._strip_newline(line, len(line))
                self.add(line)
            # Yeah, i should check for errors. sosumi.
            fclose(file_in)

cdef void c_lcase(char* buffer):
    """
    Force string to lower case
    """
    cdef unsigned int i
    for i in range(len(buffer)):
        buffer[i] = <char> tolower(buffer[i])
