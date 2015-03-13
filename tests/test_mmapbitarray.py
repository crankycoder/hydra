from _hydra import *
import tempfile

def test_ro_segfault():
    tf = tempfile.NamedTemporaryFile(delete=True)
    rw_field = MMapBitField(tf.name, 80, 0)
    rw_field[0] = 1
    ro_field = MMapBitField(tf.name, 80, 1)
    try:
        ro_field[0] = 1
    except ValueError:
        pass

def test_setitem():
    tf = tempfile.NamedTemporaryFile(delete=True)
    bf = MMapBitField(tf.name, 80, 0)

    # verify set once
    bf[0] = 1
    assert bf[0]
    for idx in range(1, len(bf)):
        assert not bf[idx]
    bf[0] = 1
    assert bf[0]
    for idx in range(1, len(bf)):
        assert not bf[idx]

    # verify unset twice
    bf[0] = 0
    for idx in range(len(bf)):
        assert not bf[idx]
    bf[0] = 0
    for idx in range(len(bf)):
        assert not bf[idx]

    # verify set at end twice
    bf[len(bf)-1] = 1
    assert bf[len(bf)-1]
    bf[len(bf)-1] = 1
    assert bf[len(bf)-1]

    # verify unset at end twice
    bf[len(bf)-1] = 0
    assert not bf[len(bf)-1]
    bf[len(bf)-1] = 0
    assert not bf[len(bf)-1]
