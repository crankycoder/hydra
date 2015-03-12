import random
from hydra import Bitmap

def test_simple_bitmap():
    x = Bitmap('/tmp/foo', 15)
    x[1] = 1
    assert x[1]

    for i, bit in enumerate(x):
        if i == 1:
            assert x[i]
        else:
            assert not x[i]

    x[1] = 0
    for bit in x:
        assert not bit

def test_giant_bitmap():
    bf_size = 10000
    x = Bitmap('/tmp/bigmap', bf_size)
    random_bits = set([random.randrange(bf_size) for i in range(2000)])
    for idx in random_bits:
        x[idx] = 1

    for i, bit in enumerate(x):
        if i in random_bits:
            assert x[i]
        else:
            assert not x[i]
