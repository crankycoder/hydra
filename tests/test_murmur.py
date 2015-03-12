import _hydra
from helpers import KeyGenerator

def test__hydra():
    # This test will probably fail on big-endian machines
    h1 = _hydra.hash('foo')
    h2 = _hydra.hash('foo', h1 & 0xFFFFFFFF)
    assert (-39287385592190013122878999397579195001, -73964642705803263641983394469427790275) == (h1, h2)

def test_collisions():
    keygen = KeyGenerator()
    hashes = {}
    for i, key in enumerate(keygen.randomKeys()):
        hcode = _hydra.hash(key)
        if hcode not in hashes:
            hashes[hcode] = key
        else:
            raise RuntimeError, "Hash collision!: %s %s" % (key, hashes[hcode])

def test_null_key():
    h0 = _hydra.hash('foo')
    h1 = _hydra.hash('foo\0bar')
    h2 = _hydra.hash('foo\0baz')
    assert h0 != h1, 'Hash collision for appended null'
    assert h0 != h2, 'Hash collision for appended null'
    assert h1 != h2, 'Hash collision for bytes after null'
