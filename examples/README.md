# Examples

All included records and effect estimates are synthetic. They are not publications, citations, or biomedical evidence. The examples make no provider requests.

Run the four end-to-end demonstrations from the repository root:

~~~bash
PYTHONPATH=src python examples/run_examples.py --output-dir /tmp/biomed-synthetic-examples
~~~

The run creates a local SQLite project plus JSON reports for original-research claim/audit state, a narrative-review matrix that preserves conflicting directions, systematic-review flow derived from saved decisions, and a meta-analysis JSON result and forest SVG. No output should be cited as a real scientific result.

The meta-analysis JSON is the explicit effect-size fixture. The systematic-review protocol, narrative-review evidence map, and original-research draft are editable templates; their unresolved markers are deliberate and must not be treated as study facts.
