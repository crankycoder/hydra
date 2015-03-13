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
