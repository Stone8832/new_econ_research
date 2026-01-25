# Public Goods Provision with Endogenous Groups (oTree 5.x)

This repository contains an oTree 5.x implementation of the experimental design in **“Public Good Provision with Endogenous Groups”** (Crockett, Oct 27, 2025).

The code implements **all four treatments** from the paper, using two oTree apps:

- `pg_exogenous` — Treatments **T1** and **T2** (exogenous firms)
- `pg_endogenous` — Treatments **T3** and **T4** (endogenous firms with live formation)

> **How to read this README:** it is intentionally long. It is designed so an instructor can understand the project **file-by-file and (effectively) line-by-line**, including the exact treatment logic, timing, payoff formulas, and matching/formation algorithms.

## Table of contents

- [Quick start](#quick-start)
- [Treatments and session configs](#treatments-and-session-configs)
- [Repository structure](#repository-structure)
- [oTree concepts used](#otree-concepts-used)
- [Global configuration: settings.py](#global-configuration-settingspy)
- [Treatment apps](#treatment-apps)
- [pg_exogenous (T1/T2): exogenous firms](#pg_exogenous-t1t2-exogenous-firms)
- [pg_endogenous (T3/T4): endogenous firms](#pg_endogenous-t3t4-endogenous-firms)
- [Templates and UI logic](#templates-and-ui-logic)
- [Automated tests (bots)](#automated-tests-bots)
- [Data/variables exported](#datavariables-exported)
- [Known deviations and implementation notes](#known-deviations-and-implementation-notes)
- [Appendix A: Paper-to-code parameter mapping](#appendix-a-paper-to-code-parameter-mapping)
- [Appendix B: Formation-state JSON schema (T3/T4)](#appendix-b-formation-state-json-schema-t3t4)
- [Appendix C: Glossary](#appendix-c-glossary)

## Quick start

### 1) Install dependencies

Python requirements are in `requirements.txt` (key dependency: `otree>=5.4.0`).

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Run the server locally

```bash
otree devserver
```

Then open the URL shown in the terminal (typically `http://localhost:8000`).

### 3) Admin login

In `settings.py`, the admin username is `admin` and the password is read from the environment variable `OTREE_ADMIN_PASSWORD`.

```bash
export OTREE_ADMIN_PASSWORD='your_password_here'
otree devserver
```

### 4) Create a session

Use the **Sessions** tab in the oTree admin UI and select one of the session configs listed below (T1–T4).

## Treatments and session configs

All treatments are configured in `settings.py` under `SESSION_CONFIGS`.

| Paper Treatment | oTree Session Config `name` | App | Formation | Internal returns | N per session | Notes |
|---|---|---|---|---|---:|---|
| **T1** | `T1_exogenous_constant` | `pg_exogenous` | exogenous | constant MPCR (Table 2) | 20 | 3 blocks × 10 rounds; one firm of each size 2–6 per block |
| **T2** | `T2_exogenous_increasing` | `pg_exogenous` | exogenous | increasing returns in effort (power function) | 20 | Uses same grouping as T1; payoff function differs |
| **T3** | `T3_endogenous_constant` | `pg_endogenous` | endogenous | constant MPCR (Table 2) | 18 | Live formation each round; autarky if unmatched |
| **T4** | `T4_endogenous_increasing` | `pg_endogenous` | endogenous | increasing returns in effort (power function) | 18 | Same formation as T3; payoff function differs |

There are additional **test** configs (`T1_test_small`, `T4_test_small`, `T3_bots_small`) that reduce N and/or shorten formation timeouts for debugging and bot testing.

## Repository structure

Top-level files (line counts shown so you can quickly locate things):

```text
.gitignore                           (14 lines)
LICENSE                              (26 lines)
Procfile                             (2 lines)
README.md                            (1 lines)
_static/global/empty.css             (0 lines)
pg_endogenous/Decision.html          (6 lines)
pg_endogenous/FirmAssignment.html    (13 lines)
pg_endogenous/Formation.html         (741 lines)
pg_endogenous/Relay.html             (25 lines)
pg_endogenous/Results.html           (17 lines)
pg_endogenous/__init__.py            (728 lines)
pg_endogenous/tests.py               (22 lines)
pg_exogenous/Decision.html           (197 lines)
pg_exogenous/Relay.html              (212 lines)
pg_exogenous/Results.html            (253 lines)
pg_exogenous/ResultsWaitPage.html    (101 lines)
pg_exogenous/Tutorial.html           (183 lines)
pg_exogenous/__init__.py             (372 lines)
pg_exogenous/_scorebar.html          (41 lines)
pg_exogenous/tests.py                (32 lines)
requirements.txt                     (6 lines)
settings.py                          (122 lines)
```

High-level purpose of each component:

- `settings.py` — global oTree configuration and the **treatment/session configs**.
- `pg_exogenous/` — the exogenous matching game (T1/T2).
- `pg_endogenous/` — the endogenous formation game with **live updates** (T3/T4).
- `_static/` — global static assets (this project includes only an empty CSS placeholder).

## oTree concepts used

This project is built with standard oTree 5.x building blocks:

- **Subsession**: one per round; used for session-wide round setup (grouping, formation state).
- **Group**: a firm/group in a given round; stores group-level outcomes (total effort, per-capita payouts).
- **Player**: one participant’s data in a given round; stores decisions and history variables.
- **Page / WaitPage**: UI screens. WaitPages are used to synchronize players and to compute payoffs.
- **`session.config`**: the per-session “treatment parameters” defined in `settings.py` (e.g., `returns_type`).
- **`participant.vars`**: per-participant persistent storage across rounds (used in T1/T2 to enforce “no repeated firm sizes” across blocks).
- **`live_method`**: oTree’s websocket-driven API for real-time interaction; used for **endogenous firm formation** in T3/T4.

## Global configuration: settings.py

File: `settings.py` (122 lines)

### What to look for

- **Lines ~5–85**: `SESSION_CONFIGS` defines the treatments. Each config selects an app and sets `returns_type` plus any needed parameters (`a`, `b`, timeouts, etc.).
- **Lines ~88–98**: `SESSION_CONFIG_DEFAULTS` includes the conversion rate (`real_world_currency_per_point=0.09`) consistent with the paper’s payment section.
- **Lines ~101–112**: `ROOMS` defines two rooms. Note: the repo does **not** currently include the `_rooms/Public_Goods_Game.txt` file referenced here (see “Known deviations” section).
- **Lines ~114–121**: admin username and password environment variable.

### Treatment parameters in `SESSION_CONFIGS`

The key switch used throughout the code is:

- `returns_type`: either `'constant'` (Table 2 MPCR) or `'increasing'` (power production function).

For `'increasing'`, the code expects parameters `a` and `b` in `session.config`. These are computed in `settings.py` using the calibration described in the paper (Appendix A).

## Treatment apps

There are two apps. Both run for **30 rounds** and use the same decision structure once firms are defined:

1. **Decision**: each subject chooses `effort_to_firm` from 0–8. Anything not allocated to the firm is kept privately at return 1 point/unit.
2. **Payoff**: `payoff = (8 - effort_to_firm) + per_capita_payout` (or `8` in autarky).
3. **Information relay**: a 30-second screen showing *per-capita effort* and *per-capita payout* by firm/firm size.

The major difference is **how firms are formed**:

- `pg_exogenous`: firms are **assigned randomly** for 10-round blocks with a constraint (no repeated size across blocks).
- `pg_endogenous`: firms are formed **each round** through a live application/accept/reject process with binding acceptance.

## pg_exogenous (T1/T2): exogenous firms

### Files

- Code: `pg_exogenous/__init__.py` (372 lines)
- Templates: `Tutorial.html`, `Decision.html`, `ResultsWaitPage.html`, `Results.html`, `Relay.html`, `_scorebar.html`
- Bots/tests: `pg_exogenous/tests.py`

### Session size and block structure (paper fidelity)

From the paper (Treatment 1):

- **20 subjects** per session.
- **30 periods** total.
- Subjects are matched into firms for **10-period intervals** (3 blocks).
- In each block there is **one firm of each size** 2, 3, 4, 5, 6.
- **No subject participates in the same firm size twice** across the 3 blocks.

This logic is implemented in `creating_session()` and `build_exogenous_matrix()`.

### Walkthrough: `pg_exogenous/__init__.py` (top-to-bottom)

Below, “Line X–Y” refers to the line numbers in `pg_exogenous/__init__.py` as shipped in this repo.

#### Imports + docstring (lines 1–17)

- Imports oTree base classes and Python utilities used for random grouping and math.
- Note: `from operator import truediv` is imported but not used (harmless).

#### Constants `C` (lines 18–42)

- `NUM_ROUNDS = 30`, `ENDOWMENT = 8` match the paper.
- `MPCR_BY_SIZE` matches Table 2 in the paper (2→0.65, …, 6→0.42).
- `BLOCK_LENGTH = 10` and `EXO_SIZES = [2,3,4,5,6]` encode the 10-round block design and the one-firm-per-size structure when N=20.

#### Block helper: `current_block_start` (lines 43–54)

- Returns the starting round of the current 10-round block: rounds 1–10 map to 1; 11–20 map to 11; 21–30 map to 21.
- Used to label firms consistently during the block (for the information relay screen).

#### Grouping algorithm: `build_exogenous_matrix` (lines 55–96)

- Inputs: full `players` list, desired firm sizes (`sizes`), and the current block start round (`current_round`).
- Goal: create groups of sizes `[2,3,4,5,6]` such that **no participant repeats a size they had in earlier blocks**.
- Method:
  - Repeatedly shuffle players and attempt to allocate them to groups (up to `max_tries`).
  - When building each group of a given size, it filters `eligible` players to those who have not previously had that size (stored in `participant.vars['size_by_block']`).
  - If at any point there are too few eligible players to form a group of the needed size, that attempt fails and the algorithm restarts.
  - If it succeeds, it returns a `matrix` suitable for `subsession.set_group_matrix()`.
- If no valid assignment is found after `max_tries`, it raises an exception (this is a protective fail-fast).

#### Session setup: `creating_session` (lines 103–159)

- Runs at the start of **each round**.
- Only on rounds **1, 11, 21** (block starts):
  - Enforces N=20 unless `test_mode=True` in the session config.
  - Sets the group matrix:
    - In `test_mode`, uses simple random pairs for convenience.
    - Otherwise calls `build_exogenous_matrix()` with the target sizes `[2,3,4,5,6]`.
  - Records each participant’s firm size for this block start in `participant.vars['size_by_block'][block_start]`.
  - Assigns a **stable “Firm ID”** (1..5) for this block and stores it in `participant.vars['firm_by_block'][block_start]`.
- On non-block-start rounds: uses `subsession.group_like_round(block_start)` to keep firms fixed for 10 rounds (paper requirement).

#### Models: `Group` and `Player` (lines 160–184)

- `Group` fields (stored each round):
  - `total_effort`, `firm_size`, `per_capita_effort`, `per_capita_payout` — used for Results and Information Relay.
- `Player` fields:
  - `effort_to_firm` is the decision variable (0..8).
  - `payoff_points` exists but is not used (payoff uses oTree’s built-in `Player.payoff`).

#### Payoff computation: `set_payoffs` (lines 185–237)

- Computes group totals from `effort_to_firm` and then computes per-capita payout using `session.config['returns_type']`:
  - **Constant returns**: `per_capita_payout = alpha(n) * total_effort` where `alpha(n)` is `MPCR_BY_SIZE[n]`.
  - **Increasing returns**: `output = a * total_effort^b` and `per_capita_payout = output / n`.
- Individual payoff: `payoff = (8 - effort_to_firm) + per_capita_payout`.
- The code intentionally raises an exception if `returns_type` is missing/unknown, to prevent running the wrong treatment by mistake.
- Note: `total_points_so_far()` is defined twice in this file (redundant but functionally identical).

#### WaitPage synchronization: `ResultsWaitPage` (lines 238–255)

- This wait page has `wait_for_all_groups = True` so that **all firms wait together**.
- This is important because the subsequent **Information Relay** screen shows outcomes for *all* firms; all group stats must be computed first.
- `after_all_players_arrive = set_payoffs_all_groups` computes payoffs for every group once everyone has submitted.

#### Pages: Tutorial → Decision → Results → Relay (lines 256–364)

- `Tutorial` is shown only in round 1.
- `Decision` is timed (`DECISION_SECONDS = 60`) and uses `timeout_submission={'effort_to_firm': 0}` matching the paper’s “auto 0 if time runs out”.
- `Results` shows a payoff breakdown (and times out after 30 seconds).
- `Relay` shows per-capita outcomes for each firm and highlights the player’s own firm using the stable Firm ID stored in `participant.vars['firm_by_block']`.

#### Page sequence (lines 365–372)

- The page order is: `Tutorial` (round 1 only) → `Decision` → `ResultsWaitPage` → `Results` → `Relay`.

### Exogenous matching algorithm details (why it works)

The “no repeated firm sizes across blocks” constraint is implemented via `participant.vars['size_by_block']`:

- At the start of each new block, the current group size is stored for each participant under the block start key (1, 11, 21).
- When forming later blocks, `build_exogenous_matrix()` checks those stored sizes and only places a participant into a size they have not previously experienced.

Because the session has exactly **one** firm of each size and each participant must fill exactly one spot, the grouping step is a constrained assignment problem; the randomized retry loop is a simple way to solve it for N=20.

## pg_endogenous (T3/T4): endogenous firms

### Files

- Code: `pg_endogenous/__init__.py` (728 lines)
- Template: `Formation.html` (contains the live UI + JavaScript)
- Templates: `FirmAssignment.html`, `Decision.html`, `Results.html`, `Relay.html`
- Bots/tests: `pg_endogenous/tests.py`

### Paper fidelity summary (Treatment 3/4)

From the paper (Treatment 3):

- **18 subjects** per session.
- **30 periods**.
- **Timing per period**:
  1. 120s firm formation (absent in T1/T2)
  2. 60s effort allocation decision
  3. 30s information relay
- Each subject is a potential firm owner. Subjects can apply to join others’ firms. Owners accept/reject in real time.
- **Binding acceptance**: once accepted, the worker cannot withdraw/apply elsewhere that period; other pending applications are canceled.
- Firm size is **capped at 6**.
- If a subject has no employees and is not employed by someone else at the end of formation, they are **autarkic** and earn 8 points.
- **Resume**: participants can view others’ history (firm, size, per-capita effort and output) and “terminations” (rejections by prior employer if the employer continues operating).

The code implements all of the above using a `live_method` for formation and a finalize step that converts formation state into the round’s group matrix.

### Walkthrough: `pg_endogenous/__init__.py` (top-to-bottom)

#### Imports + docstring (lines 1–13)

- Imports oTree API plus `json` to store the formation state as a JSON string in the Subsession.

#### Constants `C` (lines 14–34)

- Core experiment constants match the paper:
  - `NUM_ROUNDS = 30`
  - `ENDOWMENT = 8`
  - `FORMATION_SECONDS = 120`, `DECISION_SECONDS = 60`, `INFO_SECONDS = 30`
  - `MAX_FIRM_SIZE = 6`
  - `MPCR_BY_SIZE` matches Table 2 (used for constant-return treatments).
- `PLAYERS_PER_GROUP = None` because grouping is dynamic after formation.

#### Models: Subsession / Group / Player (lines 35–90)

- **Subsession fields**:
  - `formation_state` stores the JSON state for the current round’s formation process.
  - `formation_finalized` prevents double-finalization (particularly in `test_mode`).
- **Group fields** mirror `pg_exogenous` and hold group-level outcomes.
- **Player fields** include:
  - Formation outcome: `firm_owner_id`, `employer_id`, `is_autarkic`.
  - Decision: `effort_to_firm` (0..8).
  - Resume/history: `firm_members`, `firm_size`, `firm_per_capita_effort`, `firm_per_capita_payout`.
  - Termination marker: `was_terminated` (set on the *previous round* row if the player is rejected by a continuing prior employer).

#### Formation-state JSON helpers (lines 91–210)

- `_initial_state(n_players)` creates a dict with:
  - `pending[owner] = [applicants...]`
  - `accepted[owner] = [employees...]`
  - `employer[person] = owner or None`
  - `rejections = []` (used later for termination logic)
- `_get_state()` and `_set_state()` manage storing/retrieving this JSON in `Subsession.formation_state`.
- `_remove_from_all_pending()` is used to cancel all outstanding applications after a binding acceptance.
- `_auto_reject_incoming_if_owner_becomes_inactive()` implements the paper’s rule: if an owner becomes employed elsewhere, their firm becomes inactive and pending incoming applications are automatically rejected.
- `_resumes_for_all()` builds the per-player “resume” history from prior rounds and is sent to the frontend so players can inspect histories in real time.
- `_build_payload()` constructs the full data packet sent to all clients: firm lists, pending lists, employer map, outgoing applications, and resumes.

#### Round setup: `creating_session` (lines 211–239)

- Enforces N=18 unless `test_mode=True`.
- During formation, all players are placed into a **single oTree group** (`set_group_matrix([players])`).
  - This is an oTree technical detail: live pages operate within a group; using one big group allows everyone to interact in one formation “market”.
- Initializes `formation_state` fresh each round and clears `formation_finalized`.

#### Live formation API: `live_formation` (lines 240–364)

- `Formation(Page)` sets `live_method = live_formation`, so every browser can send actions in real time.
- Supported message types (`data['type']`):
  - `ping`: client heartbeat; server replies with current state (used for periodic refresh).
  - `apply`: applicant requests to join an owner’s firm.
  - `withdraw`: applicant cancels an unaccepted application.
  - `accept`: owner accepts an applicant (binding acceptance).
  - `reject`: owner rejects an applicant.
- The server enforces all paper constraints (and some additional “consistency” constraints):
  - Cannot apply to own firm.
  - Cannot apply if already employed elsewhere (binding).
  - Owners that have hired someone cannot apply elsewhere (they are bound to operate).
  - Cannot apply to inactive (grayed out) firms (owners employed elsewhere).
  - Cannot exceed max firm size 6.
- When an acceptance occurs:
  - The applicant becomes employed (`employer[applicant] = owner`).
  - All other pending applications by the applicant are canceled (`_remove_from_all_pending`).
  - The owner’s own pending applications (if any) are also canceled.
  - The applicant’s own firm becomes inactive, and any incoming pending applications to that firm are auto-rejected (`_auto_reject_incoming_if_owner_becomes_inactive`).
- Return value `{0: dict(state=...)}` broadcasts the updated state to **all players** in the formation group.

#### Finalize formation: regroup + termination marking (lines 365–507)

- Runs once per round after formation ends, and converts the JSON state into the actual oTree group structure for the decision/payoff stage.
- Steps:
  1. Auto-reject any still-pending applications at the end of formation (paper rule).
  2. Default everyone to autarky (singleton groups).
  3. For each owner who is **active** (not employed elsewhere) and has **≥1 accepted employee**, create a firm group containing `[owner] + employees`.
  4. Everyone else remains autarkic in singleton groups.
- Termination marking (paper’s “resume termination” rule):
  - A rejection counts as a reportable termination only if:
    - The rejecting owner operates a firm this period (firm continues), and
    - The applicant worked for that owner in the immediately prior period.
  - If so, the code sets `was_terminated=True` on the applicant’s **previous round** `Player` record.

#### Payoffs: `set_payoffs` (lines 508–606)

- Handles both firm groups (size ≥2) and autarky groups (size=1).
- Autarky: payoff is fixed at `ENDOWMENT = 8` points, and group statistics are set to zero.
- Firm payoff logic matches `pg_exogenous` and is controlled by `session.config['returns_type']`.
- The function also writes “resume” fields (`firm_members`, `firm_size`, per-capita stats) every round so they are available in later formation screens.

#### Pages + page sequence (lines 607–728)

- `Formation` is a **live page** (no Next button); it advances by timeout. It uses `js_vars` to send `my_id`, `max_size`, and a possibly overridden formation timeout.
- `FormationWaitPage` (not shown in `test_mode`) runs `finalize_formation` once everyone has reached the wait page.
- `FirmAssignment` shows post-formation membership (currently labeled “debug” in the template).
- `Decision` is shown only if firm size > 1 (autarkic players skip it). It uses a timed input with default 0 on timeout.
- `ResultsWaitPage` triggers payoff computation.
- `Relay` shows the per-firm-size summary table.

## Templates and UI logic

This section describes what each HTML template does and how it connects to Python code.

### `pg_exogenous` templates

- `Tutorial.html` (183 lines): explains rules, block structure, timing, and MPCR table conceptually.
- `Decision.html` (197 lines):
  - Shows firm members and provides an HTML `<input type='range'>` slider for effort (0–8).
  - Uses oTree’s implicit form submission via `name='effort_to_firm'` and `{{ next_button }}`.
- `ResultsWaitPage.html` (101 lines): customized wait page that reiterates the participant’s decision while waiting for others.
- `Results.html` (253 lines): shows a detailed payoff breakdown and visuals (progress bar).
- `Relay.html` (212 lines): shows all firms’ per-capita effort/payout; highlights the participant’s own firm using `my_firm_id` provided by Python.
- `_scorebar.html` (41 lines): a reusable component showing round number and cumulative points.

### `pg_endogenous` templates

- `Formation.html` (741 lines): **core live UI** for endogenous firm formation.
  - Frontend uses the oTree live API (`liveSend` / `liveRecv`).
  - The browser sends actions (`apply`, `withdraw`, `accept`, `reject`) and receives a full state payload.
  - The UI displays:
    - Every potential firm (one per subject) with members and pending applicants.
    - A “status” sidebar for the participant.
    - A clickable “resume” view for any player, populated from the `resumes` payload.
    - A fixed-position timer showing time remaining.
- `FirmAssignment.html` (13 lines): simple post-formation membership screen.
- `Decision.html` (6 lines): minimal decision form (could be expanded for nicer UI).
- `Results.html` (17 lines): minimal results display.
- `Relay.html` (25 lines): table of per-capita outcomes by firm size.

## Automated tests (bots)

oTree “bots” simulate participants to test flow and basic invariants.

### `pg_exogenous/tests.py`

- Each round: bot submits `effort_to_firm = 8`, visits Results, and simulates Relay timeout.
- It checks the **no repeated size across blocks** invariant by inspecting `participant.vars['size_by_block']` and verifying all sizes encountered so far are distinct.

### `pg_endogenous/tests.py`

- Formation is a live page; the bot simply times it out (no actions), proceeds through assignment, decision if applicable, results, and relay.
- This primarily tests that the round can proceed end-to-end without frontend interaction.

## Data/variables exported

When exporting oTree data, the following fields are especially important for analysis and paper replication.

### Exogenous treatments (`pg_exogenous`)

- Player-level:
  - `player.effort_to_firm` — decision (0..8)
  - `player.payoff` — realized payoff in points
- Group-level:
  - `group.firm_size`
  - `group.total_effort`
  - `group.per_capita_effort`
  - `group.per_capita_payout`
- Persistent identifiers stored in `participant.vars` (not automatically in CSV unless you add custom export):
  - `size_by_block` — mapping `{block_start_round: firm_size}` for blocks 1,11,21.
  - `firm_by_block` — mapping `{block_start_round: firm_id}` to label firms in the relay screen.

### Endogenous treatments (`pg_endogenous`)

- Player-level formation outcome each round:
  - `player.is_autarkic` (True/False)
  - `player.firm_owner_id` (0 if autarkic; otherwise owner’s id_in_subsession)
  - `player.employer_id` (0 if owner or autarkic; otherwise owner’s id_in_subsession)
- Decision:
  - `player.effort_to_firm` (only for firm members; autarky skips decision)
- Resume/history fields saved each round (used in later formation screens):
  - `player.firm_members` (comma-separated list of member IDs in the player’s firm/group)
  - `player.firm_size`
  - `player.firm_per_capita_effort`
  - `player.firm_per_capita_payout`
  - `player.was_terminated` (set on prior-round record when terminated next round)
- Group-level outcomes mirror exogenous.

## Known deviations and implementation notes

This section lists issues that do **not** prevent the experiment from running, but are relevant for grading/maintenance.

1. **Room participant label file is missing**: `settings.py` references `_rooms/Public_Goods_Game.txt`, but the `_rooms/` directory is not included in this repo. If you intend to use that room, add the missing file (one participant label per line).
2. **Duplicate function definition in `pg_exogenous/__init__.py`**: `total_points_so_far()` appears twice. This is redundant but harmless because the second definition overwrites the first with identical logic.
3. **Unused fields/imports**: `Player.payoff_points` exists but isn’t used; `operator.truediv` is imported but unused. These do not affect behavior.
4. **`info_seconds` config in endogenous test configs is currently unused**: `pg_endogenous/Relay` uses `C.INFO_SECONDS` directly. If you need variable relay time for tests, set `timeout_seconds` from `session.config` similarly to `Formation.get_timeout_seconds()`.
5. **`FirmAssignment.html` is labeled “debug”**: The paper does not forbid an intermediate “assignment summary” page, but if you want strict minimal screens, you can remove this page from `page_sequence` after confirming your desired UX.

## Appendix A: Paper-to-code parameter mapping

### Fixed parameters (all treatments)

- **Endowment**: 8 effort units per round (`C.ENDOWMENT = 8` in both apps).
- **Rounds**: 30 (`C.NUM_ROUNDS = 30`).
- **Decision timeout**: 60 seconds; default action on timeout is 0 effort to firm (implemented via `timeout_submission`).
- **Information relay**: 30 seconds.

### Table 2 MPCR values (constant-return treatments)

From the paper’s Table 2, implemented as `MPCR_BY_SIZE` in both apps:

| Firm size n | MPCR α(n) | Total return α(n)·n |
|---:|---:|---:|
| 2 | 0.65 | 1.30 |
| 3 | 0.55 | 1.65 |
| 4 | 0.49 | 1.96 |
| 5 | 0.45 | 2.25 (paper rounds to 2.24) |
| 6 | 0.42 | 2.52 (paper rounds to 2.50) |

> Note: The code uses the α values directly. Any small rounding differences in “total return” depend on decimal rounding; the model behavior matches the paper’s intent.

### Increasing returns calibration (T2 and T4)

The paper specifies a power production function for firm output:

- `output = a * E^b`, where `E` is total firm effort.
- Output is shared equally: `per_capita_payout = output / n`.

The paper calibrates `(a, b)` using the two conditions:

- `a * 16^b = 20.8` (equivalent to `16 * 1.3`)
- `a * 48^b = 120` (equivalent to `48 * 2.5`)

Solving yields:

- `b = ln(120/20.8) / ln(3) ≈ 1.5952`
- `a = 20.8 / 16^b ≈ 0.2496`

In `settings.py`, these are computed as:

```python
b = math.log(120/20.8) / math.log(3)
a = 20.8 / (16 ** b)
```

These parameters are stored in `session.config` for the increasing-return session configs and used by both apps’ payoff functions when `returns_type == 'increasing'`.

## Appendix B: Formation-state JSON schema (T3/T4)

During formation, the server stores a JSON object in `Subsession.formation_state` with the following shape:

```json
{
  "pending":  { "1": [2,5], "2": [], ... },
  "accepted": { "1": [7],   "2": [3,4], ... },
  "employer": { "1": null,  "2": 10, ... },
  "rejections": [
     {"applicant": 3, "owner": 7, "reason": "rejected"},
     {"applicant": 5, "owner": 2, "reason": "auto_end"}
  ]
}
```

Interpretation:

- Keys are stored as **strings** for JSON compatibility (`"1"`, `"2"`, …).
- `pending[owner]` are unprocessed applications to that owner’s firm.
- `accepted[owner]` are workers already hired by that owner.
- `employer[person]` is `null` if the person is not employed elsewhere; otherwise it is the owner they work for.
- `rejections` collects explicit rejections and end-of-period auto-rejections; it is later used to compute termination reporting.

## Appendix C: Glossary

- **Autarky**: a participant who is not employed by anyone and has not hired anyone in the current period (T3/T4). They earn the endowment (8 points).
- **Firm owner**: a participant operating a firm (active and has ≥1 accepted employee).
- **Binding acceptance**: once accepted into a firm, a participant cannot withdraw or apply elsewhere in that period, and their other pending applications are canceled.
- **Inactive / grayed out firm**: a potential firm whose owner is employed elsewhere; it cannot hire this period.
- **Termination (resume)**: the specific case where a participant is rejected by their prior employer *and* that employer continues operating in the current period. The termination flag is recorded on the participant’s prior-round record.

---

*README generated/updated for instructor-grade documentation (date: 2026-01-25).*