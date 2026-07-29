Read this file when a specific phrase, term, punctuation mark, or citation-syntax detail needs checking against a table. It is lookup material, not a set of rules to hold in mind while writing. The rules that govern the concision and precision passes are in [Sentence-Level Clarity](../SKILL.md#sentence-level-clarity) and [Editing Order](../SKILL.md#editing-order).

# Line Editing Tables

## Nominalizations

A verb turned into a noun needs a weak verb to carry it, so the sentence spends two words on the action and names it in the position where the reader expects a thing.

| Draft | Improved |
|---|---|
| perform a comparison of | compare |
| carry out an analysis of | analyze |
| make a measurement of | measure |
| provide an improvement in | improve |
| give an explanation for | explain |
| is used to denote | denotes |
| acts to reduce | reduces |
| was found to be | was |
| provide information about | inform, indicate |
| make an assumption | assume |
| reach a conclusion | conclude |

`A tighter generalization bound is the result of the restricted hypothesis class` becomes `The restricted hypothesis class yields a tighter generalization bound`.

## Wordy phrases

| Avoid | Use |
|---|---|
| a greater number of | more |
| despite the fact that, in spite of the fact that | although, even though |
| due to the fact that | because |
| in a number of cases | some |
| in order to | to |
| in reference to, with regard to, with respect to | about |
| in terms of | by, in, or delete |
| in the context of | delete |
| in the event that | if |
| in the vicinity of, on the order of | near, about |
| through the use of | by, with |
| is equal to, is shown to be | is |
| was found to be, was observed to be, was noted to be | was |
| it appears that, it was found that, it should be noted that, note that, it is contended that, it may be expected that | delete |
| it is apparent that | apparently |
| the results show that, the result indicates that | delete, or attach the evidence |
| the period 1977--1999 | 1977--1999 |
| in the spring of 2008 | in spring 2008 |
| on a per-iteration basis | every iteration |
| the state of California | California |

Applying these substitutions across a full draft typically removes about a fifth of its length without touching a single fact.

## Redundant pairs

Delete the parenthesized word.

(absolutely) essential · (already) existing · (alternative) choices · at (the) present (time) · (basic) fundamentals · (completely) eliminate · (completely) false · (continue to) remain · (currently) underway · (definitely) proved · empty (void) · (end) result · fewer (in number) · first (began) · (general) overview · (generally) tend to · introduced (a new) · mix (together) · (model) simulation · never (before) · none (at all) · off (of) · (overall) summary · past (experience) · period (of time) · smaller (in size) · (temporal) evolution · variety of (different) · (very) unique

## Weak nouns

Each of these names a category rather than a thing. Interrogate every use: either replace it with what it stands for, or define it precisely at first use.

ability · activity · analysis · approach · aspect · behavior · capability · case · character · concept · context · degree · development · dynamics · effect · element · environment · event · factor · influence · interaction · issue · level · manner · mechanism · nature · perspective · process · relationship · role · sense · situation · system · thing · use

`the less stable nature of the early layers` → `the early layers are less stable`. `a favorable factor for convergence` → `favoring convergence`. `a variety of factors play a role in why the model diverges` → `the model diverges for three reasons: ...`.

## Empty modifiers

Cut, or replace with the fact that would justify the judgment. The rationale, and the two that do specific damage in a paper, are under [empty intensifiers](../SKILL.md#empty-intensifiers).

actually · basically · certain(ly) · clear(ly) · current(ly) · extreme(ly) · important · interesting · kind of · naturally · now · obvious(ly) · of course · practically · quite · recent(ly) · soon · still · type of · various · very

Time words need an anchor rather than deletion: `recently` and `currently` become `as of June 2026` or `at the time of writing`, because the paper will be read years after it is written.

## Commonly misused terms

- **significant, significantly**: reserve for statistical significance, reported with the test, the statistic, the degrees of freedom, and the p-value. Used loosely it either misleads or invites a reviewer to ask for the test.
- **correlate, correlation**: use only when a correlation coefficient was computed. Otherwise `relate`, `correspond`, `track`. Note that $r$ and $r^2$ are different quantities and are routinely confused.
- **causes, causing**: a causal chain is usually inferred rather than measured. Prefer `is associated with` unless a mechanism is established; statistical association is not causation, and a plausible mechanism is the minimum entry price for causal language.
- **accuracy vs improvement over a baseline**: correspondence with the ground truth and improvement over a reference method are different quantities. A method can be accurate and add nothing over the trivial baseline, or be inaccurate and still be the best available. Say which one the number measures.
- **data**: plural in formal academic usage (`the data are`); `datum` or `data point` for one. Reserve the word for measurements, and say `model output` or `simulated fields` for what a model produced.
- **observed, seen**: for direct measurement only. For a simulation, write `occurred in the simulation` or `the model did not produce`.
- **methodology**: the study of methods. Almost always the intended word is `methods`.
- **theory**: reserved for a time-tested framework. What a paper proposes is a hypothesis, a model, or a formulation.
- **state**: means to declare definitively, as in stating a hypothesis; it is not a synonym for `say`. **claim** carries an implication that the person is not to be believed, so it colors a description of prior work.
- **objective, subjective**: an automated procedure still encodes subjective choices. Write `automated` and `manual`.
- **frequency**: per unit time. A count of events is a `number of events`.
- **why vs how**: a paper explains how something happens. `Why the error grows with depth remains unclear` usually means `How the error grows with depth has not been determined`.
- **resolution**: prefer `grid spacing` or `sampling interval`; a discretization does not resolve features at the scale of its own spacing.
- **chaos, random**: both have precise technical definitions. For a pattern that merely looks messy, write `disorganized` or `irregular`.
- **technical-sounding synonyms for plain verbs**: when the technical term names a mechanism the paper is not distinguishing, the plain verb is more precise, not less.
- **adjective--noun agreement**: qualitative adjectives belong to physical objects. Temperatures are high or low, not warm or cold; velocities are large or small, not fast or slow.
- **dates**: write `10 December 1994`. `12/10/94` denotes two different dates on two continents.
- **t test**: Student's t test, after Gosset's pen name.

## Abbreviations, numbers, statistics

- Define an abbreviation at first use as `Full Name (ABBR)` and then use the abbreviation without exception. Do not expand common field abbreviations the venue's readers use daily.
- An abbreviation used two or three times in the whole paper costs the reader more than it saves. Spell it out, or substitute a short generic (`the model`, `this scheme`).
- Never coin a citation acronym such as `JS06` for a paper. The citation command already names it.
- Measurements and decimals in numerals; whole numbers of ten or below spelled out unless they appear in a list or table with larger numbers. Spell out any number that opens a sentence, or better, rewrite so the sentence does not open with one.
- SI units. When a non-SI unit is required by convention, give the SI equivalent in parentheses at first use.
- Report a statistical test completely: test name, test statistic, degrees of freedom, p-value (`p < 0.001` suffices when it is tiny). Check the independence assumption before reporting the test at all.

## Citation syntax

- `Johnson (2001) demonstrated that ...`, not `The study by Johnson (2001) demonstrated that ...`.
- Order a parenthetical list of citations chronologically, and split a heterogeneous list by type: `theoretical analyses (...), empirical studies (...)`.
- Repeat the year at every mention of the same work; a bare surname three pages later strands the reader.
- No `see` prefix. `(see Johnson 2001)` says nothing that `(Johnson 2001)` does not.
- `e.g.` introduces an incomplete list of examples, `i.e.` restates; both take a comma after in US style. `et al.` keeps its period on `al.`
- Page ranges take an en dash: `pp. 112--119`.
- Add initials when two cited authors share a surname and a year.
- Cite the original rather than a review or a later paper that summarizes it, and cite the primary peer-reviewed source in preference to a preprint when both exist. When the original is genuinely unobtainable, write `(Sanders 1967, cited in Kessler 2008)`.
- Open and close a paragraph with your own sentences and place the cited material between them. A paragraph that begins and ends in someone else's citation reads as a compilation rather than an argument.
- Use direct quotation sparingly, always with page numbers, verbatim, with `[...]` marking any change and `[sic]` marking an error in the source.
- Read what you cite. Inheriting a characterization from another paper's citation list propagates that paper's misreadings under your name; the entailment requirement is in [Structural and Evidence Integrity](../SKILL.md#structural-and-evidence-integrity).

## Punctuation

### Commas

1. After an introductory or transitional element, when that element could be lifted out. Never place one between a gerund or infinitive subject and its verb: `Choosing a preconditioner for the system is the difficult step` takes no comma.
2. Between independent clauses joined by a conjunction. Short clauses may go without.
3. Around a nonrestrictive modifier, which can be removed, and never around a restrictive one, which cannot: `A calibration estimate, which is sufficient here, ...` against `A calibration estimate that brings the error within 1--2 dB is sufficient`. The same rule closes the appositive on both sides in `The corpus was collected in Nagoya, Japan, over three years`.
4. Between items in a series; most venues use the serial comma.
5. Between coordinate adjectives, those that could be joined by `and`: `a smaller, better-conditioned subproblem`.

### Hyphens

- Compound modifiers before the noun they modify: `end-to-end training`, `cause-and-effect relationship`. A value with its unit takes a hyphen as a modifier but not as an object: `a 128-dimensional embedding` against `an embedding of 128 dimensions`.
- Suspended hyphens keep the pattern visible: `first- and second-order methods`, `2-, 4-, and 8-layer networks`.
- Adverbs ending in `-ly` take no hyphen: `slowly converging iteration`, `widely used benchmark`. Other adverbs do when they precede the noun: `a well-known inequality`, but `the inequality is well known`.
- Prefixes are usually set solid: `reexamine`, `nonlinear`, `postprocessing`. Hyphenate before a proper noun (`trans-Atlantic`), across a tripled letter (`shell-like`), for `ex-` meaning former, and to disambiguate (`re-count` against `recount`).

### En dash and em dash

The en dash (`--` in LaTeX) is required typography rather than a stylistic choice, and the restraint on dashes in [Formatting Restraint](../SKILL.md#formatting-restraint) does not apply to it. It joins equals and spans ranges, with no surrounding spaces: `Newton--Raphson iteration`, `Kullback--Leibler divergence`, `Runge--Kutta scheme`, `Cauchy--Schwarz inequality`, `precision--recall trade-off`, `epochs 10--50`, `30\%--70\%`, `pp. 112--119`. It also joins a compound adjective containing a multiword element (`Nobel Prize--winning research`) and serves as the minus sign.

The em dash (`---`) is the one the restraint governs. It marks a break stronger than a comma, and its force comes from rarity; a paragraph with two of them has none.

## Bias-free and cross-cultural wording

- Use gender-neutral nouns (`chair`, `humanity`), pluralize to reach `they`, or rewrite to drop the pronoun. Never infer a cited author's gender from a name.
- Avoid idioms that do not survive translation (`throwing out the baby with the bathwater`, `a level playing field`). A substantial fraction of the readership reads English as a second language, and an idiom that lands for some readers is opaque to the rest.
- Define a locale-bound reference the first time it appears, whether a national benchmark, a regional dataset, a grading scale, or a currency, rather than assuming the reader shares the frame.
