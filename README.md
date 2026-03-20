# montre-py

Python bindings for [Montre](https://github.com/myersm0/montre), a fast, embeddable query engine for annotated and parallel corpora.

montre-py lets you query corpora using CQL (Corpus Query Language) directly from Python, with no server, daemon, or external process. The query engine runs in-process via a Rust shared library.

## Status

**Early prototype.** The API is functional but subject to change.

## Installation

Install the montre engine:

```bash
curl -fsSL https://raw.githubusercontent.com/myersm0/montre/main/install.sh | sh
```

Set `MONTRE_ROOT` to the montre Rust workspace root (e.g. in your shell profile):

```bash
export MONTRE_ROOT=~/path/to/montre
```

Then install the Python package:

```bash
git clone https://github.com/myersm0/montre-py
cd montre-py
pip install -e ".[pandas]"
```

## Quick start

```python
import montre

corpus = montre.open("./my-corpus")

hits = corpus.query("[pos='ADJ'] [pos='NOUN']")
hits.concordance(limit=10)
hits.frequency("lemma").most_common(10)

corpus.close()
```

## Usage

### Inspecting a corpus

```python
corpus = montre.open("./my-corpus")

corpus.token_count()
corpus.layers()        # available annotation layers: word, lemma, pos, ...
corpus.documents()
corpus.components()
corpus.alignments()
```

### Querying

```python
hits = corpus.query("[pos='ADJ'] [pos='NOUN']")
hits["word"][:5]

# restrict to a specific component
hits = corpus.query("[pos='NOUN']", component="baudelaire-fr")

# count without materializing hits
corpus.count("[pos='VERB']")
```

Single quotes in attribute values are automatically converted to double quotes, so you don't need to worry about escaping.

### Column access

A `HitList` is a table-like structure. Structural columns are always available; annotation columns are fetched on demand from the Rust engine and cached:

```python
hits["start"]          # token positions (list of int)
hits["end"]
hits["document_index"]
hits["sentence_index"]

hits["word"]           # annotation columns (fetched and cached on first access)
hits["lemma"]
hits["pos"]

hits[0]                # single row as a dict
hits.columns           # all available column names
len(hits)
```

### Concordance

`concordance` returns a KWIC (Key Word In Context) display:

```python
hits = corpus.query("[lemma='âme']")
hits.concordance(context=5, limit=10)
```

```
     les coins sombres de l'  [âme]  . -- Mais les femmes
  nous appartenaient corps…  [âme]  . Je lui dis :
```

A convenience shorthand is available directly on the corpus:

```python
corpus.concordance("[lemma='âme']", context=5, limit=10)
```

In Jupyter notebooks, concordance objects render as HTML tables automatically.

### Frequency

```python
hits.frequency("lemma").most_common(10)
corpus.frequency("[pos='NOUN']", layer="lemma", component="baudelaire-fr")
```

### Collocates

Find words that co-occur with your query target within a context window:

```python
hits.collocates(window=5, layer="lemma").most_common(10)
```

With `positional=True`, results include relative position as `(position, token)` keys, enabling distributional analysis:

```python
hits.collocates(window=5, layer="lemma", positional=True)
```

### Alignment projection

Query one language and see the aligned translations:

```python
hits = corpus.query("[lemma='âme']", component="maupassant-fr")
translated = hits.project("labse")
translated["word"][:5]
translated.concordance(limit=5)
```

### Pandas integration

```python
df = hits.to_dataframe()
df = hits.to_dataframe(layers=["word", "lemma", "pos"])
df = hits.concordance().to_dataframe()
```

### Resource management

A context manager is available for automatic cleanup:

```python
with montre.open("./my-corpus") as corpus:
    hits = corpus.query("[pos='NOUN']")
    print(len(hits), "hits")
```

For interactive or REPL use, open without `with` and call `close()` when done:

```python
corpus = montre.open("./my-corpus")
# ... work ...
corpus.close()
```

## How it works

`corpus.query()` runs the CQL query in the Rust engine and returns a `HitList` — a handle to a fully materialized result set on the Rust side. Hit positions (start, end, document, sentence) are available immediately with minimal overhead.

Annotation data (word forms, lemmas, POS tags) are fetched on demand when you access a column like `hits["lemma"]`. Each column access makes a single bulk FFI call, so the cost is one round-trip per column, not per hit. Results are cached, so subsequent access is free.

`corpus.close()` frees the Rust-side resources. If you forget, Python's garbage collector will clean up eventually, but context managers or explicit `close()` are preferred.

## API summary

**Corpus lifecycle:** `montre.open`, `corpus.close`

**Inspection:** `corpus.token_count`, `corpus.layers`, `corpus.documents`, `corpus.components`, `corpus.alignments`

**Querying:** `corpus.query`, `corpus.count`

**HitList:** `hits[column]`, `hits[index]`, `len(hits)`, `hits.columns`, `hits.concordance`, `hits.frequency`, `hits.collocates`, `hits.project`, `hits.to_dataframe`

## Requirements

- Python 3.10+
- [cffi](https://cffi.readthedocs.io/)
- Montre engine ([install](https://github.com/myersm0/montre))
- A montre corpus (built with `montre build` from CoNLL-U data)

## License

Apache-2.0
