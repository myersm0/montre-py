from . import _ffi
from ._corpus import Corpus, Component, Alignment
from ._hitlist import HitList
from ._concordance import Concordance, ConcordanceLine


def open(path):
	return Corpus(path)
