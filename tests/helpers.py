import string
import random
from os.path import join, dirname

class KeyGenerator(object):
    def __init__(self, seed = 314519):
        fname = join(dirname(__file__), 'words')
        self._fname = fname
        self._lines = open(fname,'r').readlines()
        self._linecount = len(self._lines)
        self.ELEMENTS = 10000

        self._r1 = random.Random()
        self._r1.seed(seed)

    def __len__(self):
        return self._linecount

    def __getitem__(self, i):
        start = i.start or 0
        stop = i.stop or self._linecount
        step = i.step or 1
        return self._lines[start:stop:step]

    def random_string(self, length=16):
        return "".join([self._r1.choice(string.letters+string.digits) for x in range(1, length)])

    def randomKeys(self, num_elem=None):
        '''
        Return a bunch of random keys
        '''
        if not num_elem:
            num_elem = self.ELEMENTS
        return self._r1.sample(self._lines, num_elem)

