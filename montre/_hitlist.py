from collections import Counter

from . import _ffi


structural_columns = ("start", "end", "document_index", "sentence_index")


def _normalize_cql(query):
	return query.replace("'", '"')


class HitList:
	def __init__(self, pointer, corpus):
		self._ptr = pointer
		self._corpus = corpus
		self._length = _ffi.lib.montre_hitlist_len(pointer)
		self._column_cache = {}
		self._materialize_structural()

	def _materialize_structural(self):
		length = self._length
		ptr = self._ptr
		lib = _ffi.lib
		self._column_cache["start"] = [
			lib.montre_hit_start(ptr, i) for i in range(length)
		]
		self._column_cache["end"] = [
			lib.montre_hit_end(ptr, i) for i in range(length)
		]
		self._column_cache["document_index"] = [
			lib.montre_hit_document_index(ptr, i) for i in range(length)
		]
		self._column_cache["sentence_index"] = [
			lib.montre_hit_sentence_index(ptr, i) for i in range(length)
		]

	def _fetch_layer(self, layer):
		self._corpus._check_open()
		out_len = _ffi.ffi.new("uint64_t *")
		layer_bytes = layer.encode("utf-8")
		array = _ffi.lib.montre_hitlist_texts(
			self._ptr, self._corpus._ptr, layer_bytes, out_len
		)
		if array == _ffi.ffi.NULL:
			_ffi.check_error()
			return []
		return _ffi.read_and_free_string_array(array, out_len[0])

	@property
	def columns(self):
		return list(structural_columns) + self._corpus.layers()

	def __len__(self):
		return self._length

	def __getitem__(self, key):
		if isinstance(key, str):
			if key not in self._column_cache:
				if key in structural_columns:
					raise KeyError(f"structural column {key!r} not materialized")
				self._column_cache[key] = self._fetch_layer(key)
			return self._column_cache[key]
		if isinstance(key, int):
			if key < 0:
				key += self._length
			if not 0 <= key < self._length:
				raise IndexError(f"hit index {key} out of range")
			row = {}
			for col in structural_columns:
				row[col] = self._column_cache[col][key]
			for col, values in self._column_cache.items():
				if col not in structural_columns:
					row[col] = values[key]
			return row
		raise TypeError(f"indices must be int or str, not {type(key).__name__}")

	def __iter__(self):
		for i in range(self._length):
			yield self[i]

	def concordance(self, context=5, layer="word", limit=None):
		from ._concordance import build_concordance
		return build_concordance(self, context=context, layer=layer, limit=limit)

	def frequency(self, layer="lemma"):
		return Counter(self[layer])

	def collocates(self, window=5, layer="lemma", positional=False):
		self._corpus._check_open()
		positions_ptr = _ffi.ffi.new("int32_t **")
		tokens_ptr = _ffi.ffi.new("char ***")
		offsets_ptr = _ffi.ffi.new("uint64_t **")
		out_len = _ffi.ffi.new("uint64_t *")

		_ffi.lib.montre_context_tokens(
			self._ptr, self._corpus._ptr, window,
			layer.encode("utf-8"),
			positions_ptr, tokens_ptr, offsets_ptr, out_len,
		)

		total = out_len[0]
		if total == 0:
			return Counter()

		raw_positions = positions_ptr[0]
		raw_tokens = tokens_ptr[0]
		raw_offsets = offsets_ptr[0]

		try:
			if positional:
				counts = Counter()
				for i in range(total):
					position = raw_positions[i]
					if position == 0:
						continue
					token = _ffi.ffi.string(raw_tokens[i]).decode("utf-8")
					counts[(position, token)] += 1
				return counts
			else:
				counts = Counter()
				for i in range(total):
					if raw_positions[i] == 0:
						continue
					token = _ffi.ffi.string(raw_tokens[i]).decode("utf-8")
					counts[token] += 1
				return counts
		finally:
			_ffi.lib.montre_string_array_free(raw_tokens, total)
			_ffi.lib.montre_i32_array_free(raw_positions, total)
			offset_count = self._length + 1
			_ffi.lib.montre_u64_array_free(raw_offsets, offset_count)

	def project(self, alignment_name):
		self._corpus._check_open()
		result_ptr = _ffi.lib.montre_project(
			self._corpus._ptr, self._ptr, alignment_name.encode("utf-8")
		)
		if result_ptr == _ffi.ffi.NULL:
			_ffi.check_error()
		projected = HitList.__new__(HitList)
		projected._ptr = result_ptr
		projected._corpus = self._corpus
		projected._length = _ffi.lib.montre_hitlist_len(result_ptr)
		projected._column_cache = {}
		_ffi.lib.montre_hitlist_populate_context(result_ptr, self._corpus._ptr)
		projected._materialize_structural()
		return projected

	def to_dataframe(self, layers=None):
		try:
			import pandas
		except ImportError:
			raise ImportError(
				"pandas is required for to_dataframe(); "
				"install it with `pip install pandas`"
			)
		if layers is None:
			layers = self._corpus.layers()
		data = {}
		for col in structural_columns:
			data[col] = self._column_cache[col]
		for layer in layers:
			data[layer] = self[layer]
		return pandas.DataFrame(data)

	def __del__(self):
		try:
			if hasattr(self, "_ptr") and self._ptr != _ffi.ffi.NULL:
				_ffi.lib.montre_hitlist_free(self._ptr)
		except (AttributeError, TypeError):
			pass

	def __repr__(self):
		return f"HitList({self._length} hits)"
