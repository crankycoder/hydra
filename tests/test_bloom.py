from _hydra import BloomCalculations, BloomFilter, \
    UnsupportedOperationException
from hydra import WritingBloomFilter, murmur_hash
from helpers import KeyGenerator
from nose.plugins.skip import SkipTest

BENCH_SPEC = BloomCalculations.computeBloomSpec2(15, 0.1)


def test_compute_spec():
    bs1 = BloomCalculations.computeBloomSpec1(12)
    bs2 = BloomCalculations.computeBloomSpec2(12, 0.0032)
    bs3 = BloomCalculations.computeBloomSpec1(10)

    assert bs1 == bs2
    assert bs1 != bs3
    assert bs2 != bs3


class TestFilter:
    def testManyRandom(self):
        keygen = KeyGenerator()
        MAX_HASH_COUNT = 128
        bloom = WritingBloomFilter(15, 0.0009)
        hashes = set()
        collisions = 0
        for key in keygen.randomKeys():
            for i, hashIndex in enumerate(bloom.getHashBuckets(
                    key, MAX_HASH_COUNT, 1024 * 1024)):
                hashes.add(hashIndex)
            collisions += MAX_HASH_COUNT - len(hashes)
            hashes.clear()
        assert collisions <= 100, "Got {} collisions.".format(collisions)


class TestBloomFilter(object):
    ELEMENTS = 10000
    MAX_FAILURE_RATE = 0.1

    def setup(self):
        self.bf = WritingBloomFilter(self.ELEMENTS, self.MAX_FAILURE_RATE)

    def _testFalsePositives(self, filter, keys, otherkeys):
        fp = 0

        assert len(keys) == len(otherkeys)

        for key in keys:
            filter.add(key)

        for key in otherkeys:
            if filter.contains(key):
                fp += 1

        bucketsPerElement = BloomFilter._maxBucketsPerElement(self.ELEMENTS)
        spec = BloomCalculations.computeBloomSpec2(
            bucketsPerElement, self.MAX_FAILURE_RATE)

        fp_ratio = fp / (
            len(keys) *
            BloomCalculations.PROBS[spec.bucketsPerElement][spec.K]) * 100
        assert fp_ratio < 103, "Over 103% of the maximum expected false " \
            "positives found. {:0.3f}%".format(fp_ratio)
        print "OK: Got {:0.3f}% of the expected false positives ".format(
            fp_ratio)

        # False negatives never occur - this should always work
        for k in keys:
            assert filter.contains(k)

    def testBloomLimits1(slef):
        maxBuckets = len(BloomCalculations.PROBS) - 1
        maxK = len(BloomCalculations.PROBS[maxBuckets]) - 1

        # possible
        BloomCalculations.computeBloomSpec2(
            maxBuckets, BloomCalculations.PROBS[maxBuckets][maxK])

        # impossible, throws
        try:
            BloomCalculations.computeBloomSpec2(
                maxBuckets, BloomCalculations.PROBS[maxBuckets][maxK] / 2)
            raise RuntimeError
        except UnsupportedOperationException:
            pass

    def test_one(self):
        self.bf.add("a")
        self.bf.contains("a")
        assert not self.bf.contains("b")

    def testFalsePositivesInt(self):
        keygen = KeyGenerator()
        self._testFalsePositives(self.bf,
                                 [str(x) for x in xrange(10000)],
                                 keygen.randomKeys(10000))

    def testFalsePositivesRandom(self):
        keygen1 = KeyGenerator(314159)
        self._testFalsePositives(
            self.bf,
            [keygen1.random_string() for i in range(10000)],
            [keygen1.random_string() for i in range(10000)],)

    def testWords(self):
        keygen1 = KeyGenerator()
        bf = WritingBloomFilter(
            len(keygen1)/2, self.MAX_FAILURE_RATE, ignore_case=False)

        even_keys = keygen1[::2]
        odd_keys = keygen1[1::2]
        self._testFalsePositives(bf, even_keys, odd_keys)

    def testNullKeys(self):
        assert 'foo' not in self.bf
        assert 'foo\0bar' not in self.bf
        assert 'foo\0baz' not in self.bf

        self.bf.add('foo')

        assert 'foo' in self.bf
        assert 'foo\0bar' not in self.bf
        assert 'foo\0baz' not in self.bf

        self.bf.add('foo\0bar')

        assert 'foo\0bar' in self.bf
        assert 'foo\0baz' not in self.bf

        self.bf.add('foo\0baz')

        assert 'foo\0baz' in self.bf


class TestHugeBloom():
    ELEMENTS = 1000000000
    MAX_FAILURE_RATE = 0.001

    def setup(self):
        import struct
        if 8 * struct.calcsize("P") == 32:
            raise SkipTest("Skip HugeBloom tests on 32-bit platforms")
        self.bf = WritingBloomFilter(self.ELEMENTS, self.MAX_FAILURE_RATE)

    def test_one(self):
        self.bf.add("a")
        assert self.bf.contains("a")
        assert not self.bf.contains("b")


def test_murmur():
    # Just make sure we can run the hash function from pure python
    print murmur_hash('food')


def test_unicrap():
    filter = WritingBloomFilter(100000, 0.1)
    assert u'\u2019' not in filter
    assert u'\u2018' not in filter

    filter.add(u'\u2018')
    filter.add(u'\u2019')

    filter.add('just a plain string')

    assert u'\u2019' in filter
    assert u'\u2018' in filter
    assert 'just a plain string' in filter

    assert filter[u'\u2019'] == 1
    assert filter[u'\u2018'] == 1
    assert filter['just a plain string'] == 1
