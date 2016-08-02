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


class TestFilter(object):

    def test_many_random(self):
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

    def test_hash_buckets(self):
        bloom = WritingBloomFilter(15, 0.0009)
        buckets = bloom.getHashBuckets('hydra', 128, 1024 * 1024)
        assert buckets == [
            536658, 898974, 212714, 575030, 937346, 251086, 613402,
            975718, 289458, 651774, 1014090, 327830, 690146, 3886,
            366202, 728518, 42258, 404574, 766890, 80630, 442946,
            805262, 119002, 481318, 843634, 157374, 519690, 882006,
            195746, 558062, 920378, 234118, 596434, 958750, 272490,
            634806, 997122, 310862, 673178, 1035494, 349234, 711550,
            25290, 387606, 749922, 63662, 425978, 788294, 102034,
            464350, 826666, 140406, 502722, 865038, 178778, 541094,
            903410, 217150, 579466, 941782, 255522, 617838, 980154,
            293894, 656210, 1018526, 332266, 694582, 8322, 370638,
            732954, 46694, 409010, 771326, 85066, 447382, 809698,
            123438, 485754, 848070, 161810, 524126, 886442, 200182,
            562498, 924814, 238554, 600870, 963186, 276926, 639242,
            1001558, 315298, 677614, 1039930, 353670, 715986, 29726,
            392042, 754358, 68098, 430414, 792730, 106470, 468786,
            831102, 144842, 507158, 869474, 183214, 545530, 907846,
            221586, 583902, 946218, 259958, 622274, 984590, 298330,
            660646, 1022962, 336702, 699018, 12758, 375074, 737390,
            51130, 413446]


class TestBloomFilter(object):
    ELEMENTS = 10000
    MAX_FAILURE_RATE = 0.1

    def setup(self):
        self.bf = WritingBloomFilter(self.ELEMENTS, self.MAX_FAILURE_RATE)

    def _test_false_positives(self, bf, keys, otherkeys):
        fp = 0

        assert len(keys) == len(otherkeys)

        for key in keys:
            bf.add(key)

        for key in otherkeys:
            if bf.contains(key):
                fp += 1

        bucketsPerElement = BloomFilter._maxBucketsPerElement(self.ELEMENTS)
        spec = BloomCalculations.computeBloomSpec2(
            bucketsPerElement, self.MAX_FAILURE_RATE)

        fp_ratio = fp / (
            len(keys) *
            BloomCalculations.PROBS[spec.bucketsPerElement][spec.K]) * 100
        assert fp_ratio < 103.25, "Over 103.25% of the maximum expected " \
            "false positives found. {:0.3f}%".format(fp_ratio)
        print("OK: Got {:0.3f}% of the expected false positives ".format(
            fp_ratio))

        # False negatives never occur - this should always work
        for k in keys:
            assert bf.contains(k)

    def test_bloom_limits1(self):
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
        self.bf["aa"] = 0
        assert self.bf.contains("a")
        assert "aa" in self.bf
        assert not self.bf.contains("b")
        assert "b" not in self.bf

    def test_false_positives_int(self):
        keygen = KeyGenerator()
        self._test_false_positives(
            self.bf,
            [str(x) for x in range(10000)],
            keygen.randomKeys(10000))

    def test_false_positives_random(self):
        keygen1 = KeyGenerator(314159)
        self._test_false_positives(
            self.bf,
            [keygen1.random_string() for i in range(10000)],
            [keygen1.random_string() for i in range(10000)],)

    def test_words(self):
        keygen1 = KeyGenerator()
        bf = WritingBloomFilter(
            len(keygen1) / 2, self.MAX_FAILURE_RATE, ignore_case=False)

        even_keys = keygen1[::2]
        odd_keys = keygen1[1::2]
        self._test_false_positives(bf, even_keys, odd_keys)

    def test_null_keys(self):
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


class TestHugeBloom(object):
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
    print(murmur_hash('food'))


def test_unicrap():
    bf = WritingBloomFilter(100000, 0.1)
    assert u'\u2019' not in bf
    assert u'\u2018' not in bf

    bf.add(u'\u2018')
    bf.add(u'\u2019')

    bf.add('just a plain string')

    assert u'\u2019' in bf
    assert u'\u2018' in bf
    assert 'just a plain string' in bf

    assert bf[u'\u2019'] == 1
    assert bf[u'\u2018'] == 1
    assert bf['just a plain string'] == 1
