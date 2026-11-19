# Provenance and verification notes

The Python source modules and `DATACARD.md` are exact copies from the local `engineering_question_generator` project. The source archive is also preserved. The CSV is an exact copy of the local 100,000-row output; it contains 100,000 distinct question strings.

For a record-by-record verification, the included source was run on Windows with Python 3.14 and NumPy 2.5.5. It generated a 100,000-record JSONL file containing the parameters used for each question. The included checks then re-derived every answer and passed 28,014 record-level numeric cross-checks. The JSONL is compressed in this repository.

The regenerated CSV's question, displayed answer, solution, formula, tags, and other fields match the original CSV. In 182 rows, only the auxiliary `answer_value` string differed in low-order floating-point digits between the original file and the Windows regeneration; the rounded answer text remained the same. The original CSV is preserved unchanged. The record-level verification is performed on the regenerated JSONL because it contains the parameter values needed for re-derivation; the CSV does not.

The 1,062-question PDF and workbook are a separate static output across six core branches. They are not the same file set as the 100,000-question generated dataset.

The inspected CSV has no contact-information columns. The PDF metadata uses a generic project title and author, and the workbook properties contain no personal name.
