# Product Requirements Document (PRD)

## Title

Experimental Track Promotion & Reinforcement Integration

## 0. Critical Constraint (Read First)

This work MUST be implemented as an integration into the existing radio system.

- The existing Liquidsoap, Icecast, and Python-based pipeline already works.
- The goal is not to redesign, replace, or “clean up” the current system.
- You do not have full visibility into the current architecture.

Therefore:

- Adapt this plan to the existing system.
- Do not adapt the existing system to this plan.
- Prefer minimal, additive changes over refactors.
- Reuse existing patterns, scripts, and data flows wherever possible.

If any assumption in this document conflicts with the existing system, the existing system wins.

## 1. Goal

Introduce an automated workflow that:

1. Routes all newly generated AI tracks to an experimental (staging) radio station.
2. Allows humans to explicitly approve (“good”) or reject tracks.
3. Automatically:
   - Promotes approved tracks into the main radio station.
   - Feeds metadata from approved tracks into the future generation pipeline to bias output quality.

This must be accomplished without disrupting current playout, scheduling, or generation behavior.

## 2. Non-Goals

- No replacement of Liquidsoap logic.
- No changes to Icecast topology.
- No attempt to “optimize” unrelated Python code.
- No real-time ML inference.
- No autonomous taste judgment.
- No new infrastructure dependencies.

## 3. Existing System Assumptions (Soft, Not Guaranteed)

The system likely includes:

- Liquidsoap for playout.
- Icecast for streaming.
- Python scripts that:
  - generate AI tracks
  - fill queues/playlists
  - emit now-playing metadata
- Separate experimental and main stations (mounts or playlists).
- Track generation may currently call a completely generic API that will be replaced by a real implementation later.

These are assumptions, not mandates. If the real system differs, adapt accordingly.

## 4. Core Concept

### Track Lifecycle (Logical, Not Prescriptive)

generated → experimental station → human judgment
                            → promoted → main station
                            → rejected
                            → remain experimental

Promotion is explicit and human-triggered.

How this maps to directories, playlists, or database rows is left to the implementer and MUST align with existing conventions.

## 5. Functional Requirements

### FR-1: Experimental Ingestion (Additive)

Newly generated AI tracks MUST:

- be eligible for playback on the experimental station by default
- NOT appear on the main station unless promoted

The implementation SHOULD:

- hook into existing generation outputs
- avoid duplicating generation logic
- tolerate the current generic generation API so it can be swapped later without reworking the promotion pipeline

If the current system already stages tracks somewhere, integrate at that boundary.

### FR-2: Feedback Capture (Minimal Integration)

Humans MUST be able to mark a track as:

- Good (promote)
- Bad (reject) (optional but recommended)

Feedback MAY be captured via:

- an existing interface
- a CLI
- a minimal HTTP endpoint

The system MUST persist:

- track identifier
- feedback action
- timestamp
- optional tags/notes

The mechanism MUST align with existing logging or metadata patterns if they exist.

### FR-3: Promotion Action (Atomic, Minimal)

When a track is marked “good”:

1. It MUST be made available to the main station using existing mechanisms (copy, symlink, playlist insert, DB flag, etc.).
2. It MUST be excluded from future experimental-only rotation unless explicitly desired.
3. The action MUST be reversible and traceable.

No assumptions are made about directory layout or playlist format.

### FR-4: Rejection Handling

When a track is marked “bad”:

- It MUST be excluded from promotion.
- It MAY continue to exist in experimental storage for audit/debugging.
- It MUST NOT affect main station playout.

### FR-5: Reinforcement Data Capture

For each promoted track, the system MUST retain:

- generation inputs (prompt, style, parameters, seed/template if available)
- any human tags or notes

This data MUST be fed into future generation decisions.

### FR-6: Generation Biasing (Not Control)

A periodic job SHOULD:

- analyze recently promoted tracks
- bias future generation toward:
  - styles that were promoted
  - constraints implied by human feedback
  - preserve a fixed amount of exploration

This job MUST:

- output a machine-readable plan or configuration
- be consumable by the existing generator with minimal change

## 6. Non-Functional Requirements

### Stability

- No changes should introduce dead air.
- No generation task should block playout.
- System MUST survive restarts cleanly.

### Transparency

Every promoted track MUST be traceable back to:

- when and how it was generated
- who promoted it (if available)

### Maintainability

- Prefer SQLite, flat files, or existing storage.
- Prefer systemd timers over long-running services.
- Avoid new dependencies unless absolutely necessary.

## 7. Implementation Guidance (Strong Preference)

- Follow existing code style and directory structure.
- Add new scripts rather than modifying core ones.
- Keep state transitions explicit and auditable.
- Log actions instead of silently mutating data.

## 8. Success Criteria

- Human curation effort is significantly reduced.
- Main station content is entirely human-approved.
- Experimental station remains autonomous.
- Generator output quality trends upward over time.
- No regressions in current radio behavior.

## 9. Open-Ended by Design

This document intentionally avoids:

- hard directory layouts
- exact database schemas
- UI mandates

Those decisions MUST be informed by the existing system.
