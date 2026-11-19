# CRFCE C13-NX source screen and R13-A audit

This release adds the original C13-NX source-screen package, the supporting R12-B CAD audit, and the four-page R13-A technical annex. Together they preserve the source model, recorded outputs, CAD trial, audit script, figures, and a necessary-condition result that fails the source-only traction screen.

## What the files show

The original model uses finite rectangular-coil source fields and a simplified, local saturating-polarization response. Its drive-phase screen reports a best alternating-island work of about 0.0001805 J per 80 mm. R13-A then bounds an expanded current envelope on that same stored field basis: maximum sampled tangential force is 0.2430 N, 80 mm upper work is 0.01915 J, and the sampled normal-force envelope is 0.2896 N.

These are results for one sampled surrogate. They are not nonlinear 3D FEM, Maxwell-stress validation, measured motor performance, or proof about every possible CRFCE configuration. The annex compares the sampled bounds with an 879.38 N / 70.35 J reference module and explicitly records the traction gate as failed.

## Files

- `source/` contains the original 25-file C13-NX source package: model code, input field basis, CSV/JSON outputs, original figures, README, and source checksum list.
- `r12b-cad-audit/` contains the original CAD trial, audit script, report, result files, figures, and checksum list. The STEP is a trial geometry with placeholder coil bars; it is not a manufacturing model.
- `C089363__R13A_Technical_Annex.pdf` is the original technical annex from the archive.
- `SHA256SUMS_PUBLICATION.txt` records hashes for this public copy.
- `PUBLICATION_NOTES.md` records provenance and privacy review.

The source files are preserved byte-for-byte. The mixed archive that held them was not copied because it also contained unrelated large dossier files.
