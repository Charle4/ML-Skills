Read this file whenever a bib entry needs a Tier 2 fact — a venue's official name, its abbreviated form, its identity as a journal or conference, its organizational form for a given year, or whether its title carries a `Proceedings of` prefix.

# Venue Fact Verification Protocol

Every Tier 2 fact enters the bib file through this protocol. Recall and plausibility do not: an abbreviation that looks right may truncate the wrong stem, carry a stray period, or reproduce a form the standard retired. A venue name you are confident about is still verified here, because confidence is not one of the three pillars.

## Three-Pillar Verification

A fact is established only when all three hold:

1. **Official registration** — the venue's registered title from the governing body's own record (ISSN portal for journals; the organizing society's proceedings listing for conferences).
2. **The standard's rules** — the transformation from registered title to target form, derived word by word, citing the specific rule or word entry behind each step.
3. **Independent corroboration** — ≥2 sources from **different organizations** that use the exact target form verbatim. Two pages from one publisher count as one source.

### Verdicts

- **Confirmed** — all three pillars hold. Apply the change.
- **Constructed-only** — pillars 1 and 2 hold, but fewer than 2 independent sources use the form verbatim. Leave the entry untouched and report the constructed form as unconfirmed.
- **Uncertain** — anything else: pillar 1 fails, pillar 2 cannot be derived (the standard's word list does not cover a title word), or sources disagree. Leave the entry untouched and report it as Tier 3 with every variant found. Do not pick among conflicting variants, and do not fill a gap in the word list by analogy with a word that looks similar.

## Per-Fact Requirements

**Official full name.** Pillar 1 supplies it directly. Corroborate with 2 independent sources that print the same wording.

**Abbreviated form.** All three pillars, with pillar 2 as a word-by-word table from the registered title.

**Journal vs. conference.** An ISSN record with volume/issue structure, or a publisher's journal homepage, establishes a journal; a proceedings listing under an organizing society establishes a conference. A venue that is neither confirmed is Uncertain — leave the entry type as found.

**Organizational form for a year** (`IEEE` vs `IEEE/CVF` and similar). Verify against that year's own proceedings record, not the current year's. Sources describing a different year do not corroborate.

**`Proceedings of` prefix.** Pillar 1 decides: the registered/official title either carries it or does not. Absent a clear official title, this is Uncertain — keep the source's form.

## LTWA / ISO 4

LTWA (List of Title Word Abbreviations) is maintained by the ISSN International Centre under ISO 4.

### Resources

- ISSN portal record: `https://portal.issn.org/resource/ISSN/{ISSN}`
- LTWA word list: `https://www.issn.org/wp-content/uploads/2024/02/ltwa_current.pdf`
- ISSN Manual §7.1 — rules for forming abbreviated key titles

### Rules

- Abbreviate each content word per the LTWA list; each abbreviated word ends with a period.
- Omit articles (`the`, `a`, `an`), prepositions (`of`, `on`, `in`, `for`), conjunctions (`and`, `or`).
- Keep acronyms as-is, without a period (`ACM`, `IEEE`, `SIAM`).
- Never abbreviate a one-word title.
- Retain colons, hyphens, and other punctuation from the registered title.
- LTWA entries match by stem: `comput-` covers `computer`, `computing`, `computational` → `Comput.`; `modell-` covers the British `modelling` → `Model.`.

### Independent sources

Different organizations, e.g.: DBLP (prints an explicit `ISO 4 abbr.` field), MathSciNet serials list, SIAM serials list, the publisher's journal page (Elsevier, Springer, Wiley), Paperpile's abbreviation database, NLM catalog, university library journal databases.

### Conferences under LTWA

Conferences generally hold no ISSN registration, so pillar 1 yields an official proceedings title rather than a registered key title, and any abbreviation is *constructed* from LTWA rules. Where fewer than 2 independent sources reproduce the constructed form verbatim, the verdict is Constructed-only: leave the entry untouched and report the proposed form rather than presenting it as an official abbreviation.

## Processing a Bib File

1. Collect the unique venue names and the Tier 2 questions each one raises. Verify per unique venue, not per entry.
2. Run the protocol for each, recording the verdict and its sources.
3. Apply Confirmed forms to every entry sharing that venue; leave Constructed-only and Uncertain venues untouched.
4. Report: Confirmed forms with their sources; Constructed-only forms with the missing corroboration; Uncertain venues with their conflicting variants.

The three pillars hold for any abbreviation standard — LTWA, an IEEE style, a publisher's house list. The governing body and word rules change; official registration, the standard's rules, and independent corroboration do not.
