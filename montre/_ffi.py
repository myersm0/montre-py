import os
import cffi

ffi = cffi.FFI()

ffi.cdef("""
	// error handling
	const char *montre_last_error(void);

	// string handling
	void montre_string_free(char *s);
	void montre_string_array_free(char **array, uint64_t len);
	void montre_i32_array_free(int32_t *array, uint64_t len);
	void montre_u64_array_free(uint64_t *array, uint64_t len);

	// corpus lifecycle
	void *montre_corpus_open(const char *path);
	void montre_corpus_close(void *corpus);
	uint64_t montre_corpus_token_count(const void *corpus);

	// corpus metadata
	uint32_t montre_corpus_layer_count(const void *corpus);
	char *montre_corpus_layer_name(const void *corpus, uint32_t index);
	uint32_t montre_corpus_document_count(const void *corpus);
	char *montre_corpus_document_name(const void *corpus, uint32_t index);
	uint32_t montre_corpus_component_count(const void *corpus);
	char *montre_corpus_component_name(const void *corpus, uint32_t index);
	char *montre_corpus_component_language(const void *corpus, uint32_t index);

	// alignments
	uint32_t montre_corpus_alignment_count(const void *corpus);
	char *montre_corpus_alignment_name(const void *corpus, uint32_t index);
	char *montre_corpus_alignment_source(const void *corpus, uint32_t index);
	char *montre_corpus_alignment_target(const void *corpus, uint32_t index);
	uint64_t montre_corpus_alignment_edge_count(const void *corpus, uint32_t index);

	// token access
	char *montre_corpus_token_annotation(
		const void *corpus, uint64_t position, const char *layer
	);
	char *montre_corpus_span_text(
		const void *corpus, uint64_t start, uint64_t end, const char *layer
	);

	// query
	void *montre_query(const void *corpus, const char *cql);
	void *montre_query_in_component(
		const void *corpus, const char *cql, const char *component
	);
	int64_t montre_query_count(const void *corpus, const char *cql);

	// hitlist
	void montre_hitlist_free(void *hits);
	uint64_t montre_hitlist_len(const void *hits);
	uint64_t montre_hit_start(const void *hits, uint64_t index);
	uint64_t montre_hit_end(const void *hits, uint64_t index);
	uint32_t montre_hit_document_index(const void *hits, uint64_t index);
	uint32_t montre_hit_sentence_index(const void *hits, uint64_t index);
	void montre_hitlist_populate_context(void *hits, const void *corpus);

	// bulk text extraction
	char **montre_hitlist_texts(
		const void *hits, const void *corpus, const char *layer, uint64_t *out_len
	);

	// context tokens
	void montre_context_tokens(
		const void *hits, const void *corpus, uint32_t window, const char *layer,
		int32_t **out_positions, char ***out_tokens,
		uint64_t **out_offsets, uint64_t *out_len
	);

	// projection
	void *montre_project(
		const void *corpus, const void *source_hits, const char *alignment_name
	);
""")


def _find_library():
	root = os.environ.get("MONTRE_ROOT")
	if root is None:
		raise RuntimeError(
			"MONTRE_ROOT environment variable not set; "
			"it should point to the montre repository root"
		)
	path = os.path.join(root, "target", "release")
	for name in ("libmontre_ffi.so", "libmontre_ffi.dylib", "montre_ffi.dll"):
		candidate = os.path.join(path, name)
		if os.path.exists(candidate):
			return candidate
	raise RuntimeError(
		f"could not find libmontre_ffi in {path}; "
		"run `cargo build --release` in the montre workspace"
	)


lib = ffi.dlopen(_find_library())


def check_error():
	error_ptr = lib.montre_last_error()
	if error_ptr != ffi.NULL:
		message = ffi.string(error_ptr).decode("utf-8")
		raise RuntimeError(message)


def read_and_free_string(ptr):
	if ptr == ffi.NULL:
		return None
	try:
		return ffi.string(ptr).decode("utf-8")
	finally:
		lib.montre_string_free(ptr)


def read_and_free_string_array(array, length):
	if array == ffi.NULL:
		return []
	try:
		return [ffi.string(array[i]).decode("utf-8") for i in range(length)]
	finally:
		lib.montre_string_array_free(array, length)
