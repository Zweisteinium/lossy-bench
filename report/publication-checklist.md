# Before this repository goes public

The tracked tree contains no audio, no credentials and no provenance fields. The originals of the reduced files are
kept outside git. What is left to decide or do:

- [ ] **Artist and title in paths.** Nearly every data file identifies songs by their library path, which makes the
      results checkable. Keep this as metadata, or replace it with stable file ids.
- [ ] **Licence:** for the code (e.g. MIT) and the data (e.g. CC BY 4.0, metadata only). There is none yet, so all
      rights are reserved.
- [ ] `CITATION.cff` with authors and version.
- [ ] Tag a release; archive the data on Zenodo for a DOI.
- [ ] Pin the tools: lossprint 1.1.0 from crates.io, flaccheck at its commit (docs/methods.md), and the Echolot image
      of commit e9f0bf9 (rebuildable from the public Echolot repository).
- [ ] Disclose the use of AI assistants for running the study and drafting the text, if the target venue asks for
      it.
