# Technical-diagram review log

Companion material to the human-facing walkthrough in the repository root [`README.md`](../README.md).
The eight figures it reviews live in [`figures/`](figures/) and are produced by
[`generate_pikvm_diagrams.py`](generate_pikvm_diagrams.py); deterministic QA is
[`critic_checks.py`](critic_checks.py).

## Reviewer limitations

A second LLM/subagent could not be launched in this environment. To avoid implying an independent AI review, this package contains a **separate reproducible programmatic critic** (`critic_checks.py`) and a **manual editorial critique**, not an actual independent subagent. Ratings below are author-side judgments, not third-party verification. No physical PiKVM was tested.

## Criteria

- **A — Accuracy (1–5):** map from code/docs to figure is defensible; commands, endpoint relationships, coordinate values, and limitations match the pinned revision.
- **C — Clarity (1–5):** readable at presentation size, evident direction of flow, limited jargon, explicit meaning of measurements.
- **P — Polish (1–5):** hierarchy, legibility, consistent typography, contrast, alignment, and crop/box boundaries.
- Target for course use: **all criteria ≥4/5**. Ratings do not replace peer review.

| Step | A | C | P | Critique and final decision |
|---|---:|---:|---:|---|
| 01 Setup | 5 | 5 | 5 | Replaced an overflowing quoted request with a shorter one; endpoint resolution remains explicit and has a blocked branch. |
| 02 Preflight | 5 | 5 | 5 | Each read-only endpoint is distinguished. ATX caveat retained to prevent interpreting status as screen evidence. |
| 03 Fresh frame | 5 | 4 | 5 | Screenshot mock originally had overlapping text at small scale. Abbreviated screen labels. Viewer still needs to understand that the screen is illustrative. |
| 04 Crop | 5 | 5 | 5 | Made crop origin and local offsets numerically consistent. Reduced crowded math label and small target marker. |
| 05 Coordinates | 5 | 5 | 4 | Rebuilt the whole layout after initial equations covered the coordinate grids. Final two coordinate origins and the arithmetic are visible. |
| 06 HID | 5 | 5 | 5 | Initial full REST URL overflowed its dark panel. Split endpoint and query, preserving exact values and event order. |
| 07 Verify | 5 | 5 | 5 | Moved image frames down so BEFORE/AFTER titles sit outside their screenshots; the visible change is explicit. |
| 08 Recovery | 5 | 5 | 5 | Shortened footer to avoid collision with source attribution. Failure branches distinguish retryable and stop conditions. |

## Mechanical validation

Run `python critic_checks.py` for checks including:

1. Exact pixel→KVMD mapping `1920×1200 @ (1440,900) = (16384,16384)`, center `(960,600) = (0,0)`, edge clipping and zoom offsets.
2. Eight PNG and eight SVG files exist; PNG dimensions are 2080×1170 and pixel variance confirms nonblank content.
3. Seven core text-on-background combinations have WCAG contrast ratios **≥4.5:1**. This is a targeted color audit, not a full automated accessibility audit.

## Remaining caveats

- Actual UI screenshots will not match the mock. The diagrams explain mechanisms and decisions, not exact appearance of PiKVM's frontend.
- The simulated 'Details' button is a harmless teaching example; real actions can be irreversible.
- Actual mouse calibration and hardware support should be confirmed against the target PiKVM build and monitor mode.
- Human review is not the same as a second independent LLM critique. Independent peer review remains recommended before publication.
