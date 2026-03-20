from collections import Counter

from . import _ffi
from ._hitlist import HitList, _normalize_cql


class Component:
	__slots__ = ("name", "language")

	def __init__(self, name, language):
		self.name = name
		self.language = language

	def __repr__(self):
		return f"Component({self.name!r}, language={self.language!r})"


class Alignment:
	__slots__ = ("name", "source", "target", "edge_count")

	def __init__(self, name, source, target, edge_count):
		self.name = name
		self.source = source
		self.target = target
		self.edge_count = edge_count

	def __repr__(self):
		return (
			f"Alignment({self.name!r}, "
			f"{self.source!r} -> {self.target!r}, "
			f"{self.edge_count} edges)"
		)


class Corpus:
	def __init__(self, path):
		self._ptr = _ffi.lib.montre_corpus_open(path.encode("utf-8"))
		if self._ptr == _ffi.ffi.NULL:
			_ffi.check_error()
		self._layers = None
		self._documents = None

	def __enter__(self):
		return self

	def __exit__(self, *args):
		self.close()

	def close(self):
		if self._ptr != _ffi.ffi.NULL:
			_ffi.lib.montre_corpus_close(self._ptr)
			self._ptr = _ffi.ffi.NULL

	def token_count(self):
		return _ffi.lib.montre_corpus_token_count(self._ptr)

	def layers(self):
		if self._layers is None:
			count = _ffi.lib.montre_corpus_layer_count(self._ptr)
			self._layers = [
				_ffi.read_and_free_string(
					_ffi.lib.montre_corpus_layer_name(self._ptr, i)
				)
				for i in range(count)
			]
		return list(self._layers)

	def documents(self):
		if self._documents is None:
			count = _ffi.lib.montre_corpus_document_count(self._ptr)
			self._documents = [
				_ffi.read_and_free_string(
					_ffi.lib.montre_corpus_document_name(self._ptr, i)
				)
				for i in range(count)
			]
		return list(self._documents)

	def components(self):
		count = _ffi.lib.montre_corpus_component_count(self._ptr)
		result = []
		for i in range(count):
			name = _ffi.read_and_free_string(
				_ffi.lib.montre_corpus_component_name(self._ptr, i)
			)
			language = _ffi.read_and_free_string(
				_ffi.lib.montre_corpus_component_language(self._ptr, i)
			)
			result.append(Component(name, language))
		return result

	def alignments(self):
		count = _ffi.lib.montre_corpus_alignment_count(self._ptr)
		result = []
		for i in range(count):
			name = _ffi.read_and_free_string(
				_ffi.lib.montre_corpus_alignment_name(self._ptr, i)
			)
			source = _ffi.read_and_free_string(
				_ffi.lib.montre_corpus_alignment_source(self._ptr, i)
			)
			target = _ffi.read_and_free_string(
				_ffi.lib.montre_corpus_alignment_target(self._ptr, i)
			)
			edge_count = _ffi.lib.montre_corpus_alignment_edge_count(self._ptr, i)
			result.append(Alignment(name, source, target, edge_count))
		return result

	def query(self, cql, component=None):
		normalized = _normalize_cql(cql)
		if component is not None:
			ptr = _ffi.lib.montre_query_in_component(
				self._ptr,
				normalized.encode("utf-8"),
				component.encode("utf-8"),
			)
		else:
			ptr = _ffi.lib.montre_query(self._ptr, normalized.encode("utf-8"))
		if ptr == _ffi.ffi.NULL:
			_ffi.check_error()
		_ffi.lib.montre_hitlist_populate_context(ptr, self._ptr)
		return HitList(ptr, self)

	def count(self, cql):
		normalized = _normalize_cql(cql)
		result = _ffi.lib.montre_query_count(self._ptr, normalized.encode("utf-8"))
		if result < 0:
			_ffi.check_error()
		return result

	def concordance(self, cql, component=None, context=5, layer="word", limit=None):
		hits = self.query(cql, component=component)
		return hits.concordance(context=context, layer=layer, limit=limit)

	def frequency(self, cql, layer="lemma", component=None):
		hits = self.query(cql, component=component)
		return hits.frequency(layer=layer)

	def __del__(self):
		try:
			if hasattr(self, "_ptr") and self._ptr != _ffi.ffi.NULL:
				self.close()
		except (AttributeError, TypeError):
			pass

	def __repr__(self):
		return f"Corpus({self.token_count()} tokens, {len(self.layers())} layers)"
