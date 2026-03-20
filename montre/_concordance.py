from . import _ffi


class ConcordanceLine:
	__slots__ = ("left", "match", "right", "document", "position")

	def __init__(self, left, match, right, document, position):
		self.left = left
		self.match = match
		self.right = right
		self.document = document
		self.position = position

	def __repr__(self):
		return f"{self.left:>40s}  [{self.match}]  {self.right}"


class Concordance:
	def __init__(self, lines):
		self._lines = lines

	def __len__(self):
		return len(self._lines)

	def __getitem__(self, key):
		return self._lines[key]

	def __iter__(self):
		return iter(self._lines)

	def __repr__(self):
		parts = [repr(line) for line in self._lines]
		return "\n".join(parts)

	def _repr_html_(self):
		rows = []
		for line in self._lines:
			rows.append(
				f"<tr>"
				f"<td style='text-align:right'>{_escape(line.left)}</td>"
				f"<td style='text-align:center;font-weight:bold'>{_escape(line.match)}</td>"
				f"<td style='text-align:left'>{_escape(line.right)}</td>"
				f"<td style='color:gray'>{_escape(line.document)}</td>"
				f"</tr>"
			)
		return (
			"<table>"
			"<tr><th style='text-align:right'>Left</th>"
			"<th>Match</th>"
			"<th style='text-align:left'>Right</th>"
			"<th>Document</th></tr>"
			+ "".join(rows)
			+ "</table>"
		)

	def to_dataframe(self):
		try:
			import pandas
		except ImportError:
			raise ImportError(
				"pandas is required for to_dataframe(); "
				"install it with `pip install pandas`"
			)
		return pandas.DataFrame([
			{
				"left": line.left,
				"match": line.match,
				"right": line.right,
				"document": line.document,
				"position": line.position,
			}
			for line in self._lines
		])


def _escape(text):
	return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_concordance(hitlist, context=5, layer="word", limit=None):
	corpus = hitlist._corpus
	lib = _ffi.lib
	ffi = _ffi.ffi

	count = len(hitlist)
	if limit is not None:
		count = min(count, limit)

	token_total = lib.montre_corpus_token_count(corpus._ptr)
	layer_bytes = layer.encode("utf-8")
	documents = corpus.documents()

	lines = []
	for i in range(count):
		start = hitlist._column_cache["start"][i]
		end = hitlist._column_cache["end"][i]
		document_index = hitlist._column_cache["document_index"][i]

		left_start = max(0, start - context)
		right_end = min(token_total, end + context)

		left_ptr = lib.montre_corpus_span_text(
			corpus._ptr, left_start, start, layer_bytes
		)
		match_ptr = lib.montre_corpus_span_text(
			corpus._ptr, start, end, layer_bytes
		)
		right_ptr = lib.montre_corpus_span_text(
			corpus._ptr, end, right_end, layer_bytes
		)

		left_text = _ffi.read_and_free_string(left_ptr) or ""
		match_text = _ffi.read_and_free_string(match_ptr) or ""
		right_text = _ffi.read_and_free_string(right_ptr) or ""

		document_name = documents[document_index] if document_index < len(documents) else ""

		lines.append(ConcordanceLine(
			left=left_text,
			match=match_text,
			right=right_text,
			document=document_name,
			position=start,
		))

	return Concordance(lines)
