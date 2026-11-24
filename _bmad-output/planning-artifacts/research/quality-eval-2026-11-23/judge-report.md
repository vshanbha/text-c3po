# Judge report — quality pairs (BLIND, written before key was opened)

Judge: MiMo (agent judge; not a contestant — neither lfm3 nor ornith).
Date: 2026-11-23. Sheet: `sheet.md` (12 pairs, A/B randomized per pair).
Rubric: adequacy (meaning) / completeness / fluency / register; evidence
cited per pair; ties allowed. This file was written while `judge-key.md`
remained unopened.

## Per-pair judgments

### Pair 1 — German, "Where is the train station?"
- **A** formal: "Die Bahnhofsstation befindet sich in der Stadt." — turns the
  question into a statement AND invents "in der Stadt" (not in input).
  Informal: "Der Bahnhof ist dort!" — same two failures ("dort" invented).
  Adequacy: FAIL on both.
- **B** formal: "Wo befindet sich der Bahnhof?" / informal: "Wo ist der
  Bahnhof?" — both correct questions, nothing added.
- **Winner: B** (adequacy decisive). Fluency: both fine. Register: both fine.

### Pair 2 — German, "Thank you very much for your help."
- **A** formal: "Vielen Dank für Ihre Hilfe." (Ihre = formal ✓); informal:
  "Danke für deine deine…" → "Danke für deine Hilfe." (du ✓) — complete.
- **B** formal: identical to A ✓; informal: "Vielen Dank!" — **drops "for
  your help"** (completeness fail).
- **Winner: A** (completeness + register). 

### Pair 3 — German, "The meeting starts at three o'clock."
- A formal "Die Sitzung beginnt um drei Uhr." == B formal; informals
  "Der Termin startet…" (A) vs "Die Besprechung startet…" (B) — both
  natural, both complete, register appropriate.
- **Winner: TIE** on every dimension.

### Pair 4 — German, "I would like a coffee, please."
- A formal "Ich möchte gerne einen Kaffee, bitte." ✓; A informal "Ich hätte
  gern einen Kaffee, bitte." ✓ (complete).
- B formal "Ich würde gerne einen Kaffee haben, bitte." ✓; B informal
  "Kaffee, bitte!" — elliptical: drops "I would like" (register licenses
  ellipsis, but literally less complete).
- **Winner: A (narrow)** — completeness only; adequacy/fluency/register tie.

### Pair 5 — German, "She reads a book every evening." (the Sie trap)
- A formal "Sie liest jeden Abend ein Buch." ✓; A informal **"Du liest…"**
  — changes the subject from *she* to *you* (person change: FAIL).
- B formal identical ✓; B informal **"Er liest…"** — keeps 3rd person but
  flips gender she→he (FAIL, milder: referent gender only).
- Note: correct "informal" for a 3rd-person subject is unchanged "Sie
  liest…"; both models wrongly tried to de-formalize.
- **Winner: B (narrow)** — smaller identity error (gender vs person).

### Pair 6 — German, lighthouse 10 paragraphs (long) ★
- **A: first sentence only** — 1 of 10 paragraphs, formal and informal
  both. 9 paragraphs dropped. Completeness: CATASTROPHIC FAIL.
- **B: full 10 paragraphs**, both registers, idiomatic ("längst
  erloschen", "schwarze Wolken verschlangen den Horizont").
- **Winner: B** (decisive on completeness; adequacy of A's one paragraph
  is fine but irrelevant next to 90% loss).

### Pair 7 — Spanish, "Where is the train station?"
- A formal "¿Dónde se encuentra la estación de tren?" / informal
  "¿Dónde está…?" — correct questions.
- B formal "La estación de tren se encuentra en la ciudad central." /
  informal "…está en el centro de la ciudad." — statements, and **adds
  "central city"** not in input (same failure pattern as Pair 1-A).
- **Winner: A** (adequacy decisive).

### Pair 8 — Spanish, "Thank you very much for your help."
- A: "Muchas gracias por su ayuda." (su ✓) / "¡Muchas gracias por tu
  ayuda!" (tu ✓) — idiomatic.
- B: "Gracias mucho por su ayuda." / "¡Gracias muchísimo!" — both
  **unidiomatic** (correct: "Muchas gracias" / "muchísimas gracias").
- **Winner: A** (fluency + register).

### Pair 9 — Spanish, "The meeting starts at three o'clock."
- A formal "…a las tres en punto." ✓; B formal "…a las tres **de la
  tarde**." — adds p.m. (input says three o'clock, not afternoon).
- Informals identical ("La reunión arranca a las tres.").
- **Winner: A (narrow)** — adequacy (B adds an assumption); rest tie.

### Pair 10 — Spanish, "I would like a coffee, please."
- Both models produced byte-identical outputs: formal "Me gustaría un
  café, por favor." / informal "Quiero un café, por favor."
- **Winner: TIE** (all dimensions; note "Quiero" = "I want" is blunter
  than "I would like" but it is *both* models' identical choice).

### Pair 11 — Spanish, "She reads a book every evening."
- A: "Lee un libro cada noche." (subject elided — idiomatic; informal ==
  formal). B: "Ella lee un libro cada noche." / "…todas las noches." —
  explicit subject, same meaning. "noche" vs "evening" shift present in
  both equally.
- **Winner: TIE** (all dimensions).

### Pair 12 — Spanish, lighthouse 10 paragraphs (long) ★
- **Both complete** (10/10 paragraphs each) — completeness tie.
- **A**: "los **gavilanes**" (sparrowhawks — input says gulls), "**alomoches**"
  (non-word, ×2 — should be "aleros"), "el amanecer se despertara" (dawn
  "would wake up" — mistranslation of "dawn broke clear"), "el pueblo se
  felicitó" (the town congratulated itself), informal "pájaros de
  marilla" (non-word) + "se acostumbraron en las alomoches" (nested →
  "got used to"), "la luz nunca se quedó sin luz" (tautology).
- **B**: "acantilado" (cliff ✓ vs A's "roca"), "farero" (keeper ✓),
  "gaviotas" (gulls ✓), "aleros" (eaves ✓), "la junta del faro envió
  ingenieros" — consistently accurate and natural in both registers.
- **Winner: B** (adequacy + fluency decisive).

## Blind tally (per pair, before decoding)

| Dimension | A | B | Ties |
|---|---|---|---|
| Overall wins | 5 (P2, P4, P7, P8, P9) | 4 (P1, P5, P6, P12) | 3 (P3, P10, P11) |
| Decisive margins | P7, P8 | **P6, P12** (both long inputs) | — |

Observations independent of identity:
1. **The long inputs split hardest**: one side collapsed to a single
   paragraph in German (P6); the other side carried junk vocabulary in
   Spanish (P12: "alomoches", "gavilanes").
2. **Question-to-statement failure appeared on one side in both
   languages** (P1-A German, P7-B Spanish) — a systematic adequacy
   pattern, not a one-off.
3. **Register handling** (Sie/du, su/tu) was correct on both sides
   except the P5 third-person trap where both erred.

*Key unopened at time of writing.*

---

# Key decoding (appended AFTER judgments were written)

| Pair | Blind winner | A | B | Winner model |
|---|---|---|---|---|
| 1 | B | lfm3 | ornith | **ornith** |
| 2 | A | ornith | lfm3 | **ornith** |
| 3 | TIE | ornith | lfm3 | tie |
| 4 | A (narrow) | ornith | lfm3 | **ornith** |
| 5 | B (narrow) | lfm3 | ornith | **ornith** |
| 6 | B (decisive) | lfm3 | ornith | **ornith** |
| 7 | A | ornith | lfm3 | **ornith** |
| 8 | A | ornith | lfm3 | **ornith** |
| 9 | A (narrow) | ornith | lfm3 | **ornith** |
| 10 | TIE | ornith | lfm3 | tie |
| 11 | TIE | lfm3 | ornith | tie |
| 12 | B (decisive) | lfm3 | ornith | **ornith** |

## Final tally

**ornith-1.5: 9 wins, lfm3: 0 wins, 3 ties** (12 pairs, DE+ES).

- ornith won every decisive pair; lfm3's losses include systematic
  patterns: question→statement with invented content (P1 DE, P7 ES),
  unidiomatic Spanish (P8 "Gracias mucho"), content-dropping informal
  (P2 DE), worse identity error in the Sie/du third-person trap (P5),
  junk vocabulary in ES long (P12 "alomoches"/"gavilanes"), and the
  **German long-input first-sentence collapse (P6) — a live bug**.
- Caveats: n=12, two languages, single sample per cell, one judge
  (model-dependent, advisory). Directionally consistent and each loss
  cites specific errors — treat as strong signal, not final verdict.

## Bug filed from this eval (found nothing else could)

P6 decoded to lfm3: German long input still returns first-sentence-only
(79 chars) at think-off WITH the da799e2 fix — verification had covered
Spanish only. Confirmed 5/5 deterministic at app path; ornith control
878 full. German isolation: plain prompt FULL (864), json formal-only
FULL (844), json 3-field SHORT (79), think-on FULL but 339s. Trigger
narrowed to: dual formal+informal requirement × long input × German ×
think-off. Candidate fix: input-side chunking (short dual-output cells
are proven by the gate) — story-sized, not a prompt tweak.
