---
name: bead-planner
description: >
  Converts a feature discussion, design doc, or planning session into rich,
  context-laden beads (issues) that polecats can execute independently.
  Use this skill whenever someone says "break this into beads", "plan this feature",
  "create issues for this", or after a design convoy or planning conversation
  produces a plan that needs to become actionable work items.
---

# Bead Planner

You turn plans into work. After a planning conversation, design convoy, or feature
discussion, you produce beads that are rich enough for an ephemeral polecat — with
no prior context — to pick up and execute successfully.

## Why This Matters

Polecats are ephemeral. They get spawned, receive a bead, do the work, and
self-destruct. They don't have access to the planning conversation, the design doc,
or your mental model. The bead description IS their entire world. A thin bead
("add sharing feature") produces bad work. A rich bead produces good work.

## The Process

### Step 1: Gather the Plan

Identify what you're working from. This could be:

- A conversation you just had about a feature
- A design doc from `gt formula run design` (check `.designs/`)
- A set of notes or requirements from the overseer
- An existing bead that's too large and needs decomposition

If working from a design doc, read it:
```bash
ls .designs/
cat .designs/<latest>/design-doc.md
```

If working from conversation context, summarize the key decisions, requirements,
and constraints before proceeding.

### Step 2: Understand the Codebase Context

Before writing beads, you need to know what a polecat will need to navigate the
code. Explore the relevant parts of the codebase:

```bash
# Understand the project structure
ls -la
find . -name "*.go" -o -name "*.py" -o -name "*.ts" | head -30

# Find the files most relevant to the feature
grep -r "relevant_term" --include="*.go" -l

# Read key files to understand conventions
cat <main_file_path>
```

Collect:

- **Key file paths** the polecat will need to touch or read
- **Naming conventions** used in the codebase (function names, package structure)
- **Existing patterns** the polecat should follow (how are similar features built?)
- **Dependencies** (what packages/modules are already used for related functionality)
- **Test patterns** (how are tests structured? what test framework?)

### Step 3: Decompose Into Beads

Break the plan into beads that are:

- **Independently executable** — a polecat can complete one bead without waiting
  for another (unless you explicitly set up dependency via `--blocks`)
- **Appropriately scoped** — a single bead should be completable in one session
  (roughly 1-3 hours of focused agent work)
- **Vertically sliced** where possible — each bead delivers something testable,
  not "write all the models" then "write all the handlers"

Good decomposition patterns:

- Feature bead per user-facing behavior ("users can share a recipe via link")
- Infrastructure bead for shared foundations ("add shares table and model")
- Integration bead for wiring things together ("connect share API to frontend")

Bad decomposition:

- Layer-cake slicing ("do all database work" / "do all API work" / "do all tests")
- Too granular ("add field X to struct" as its own bead)
- Too broad ("implement the entire sharing feature")

### Step 4: Write Rich Bead Descriptions

Each bead description should follow this template. Not every section is needed
for every bead — use judgment — but err on the side of more context.

```
## What
One paragraph: what does this bead accomplish? What's the user-visible or
system-visible outcome?

## Why
One sentence: why does this matter? What's it enabling? This helps the polecat
make good judgment calls when requirements are ambiguous.

## Acceptance Criteria
Bulleted list of specific, testable conditions that define "done":
- Criterion 1
- Criterion 2
- Each criterion should be verifiable by running tests or inspecting output

## Technical Context
- **Key files**: paths the polecat will need to read or modify
- **Patterns to follow**: point to existing code that does something similar
  ("see how handlers/recipe.go implements CRUD — follow that pattern")
- **Dependencies**: packages, modules, or services this work depends on
- **Data model**: relevant structs, schemas, or types

## Constraints
- Hard limits (must use existing SQLite, no new dependencies, etc.)
- Performance requirements if any
- Security considerations if any

## Out of Scope
What this bead should NOT do. This prevents gold-plating and scope creep.

## Related
- Links to other beads this depends on or blocks
- Reference to design doc if one exists
- Any relevant prior art or decisions made during planning
```

### Step 5: Create the Beads

Use `bd create` with the full description. For multi-line descriptions, use
heredoc syntax:

```bash
bd create --title="Add recipe sharing endpoint" \
  --type=task --priority=2 \
  --description="$(cat <<'BEAD'
## What
Add a POST /api/recipes/:id/share endpoint that generates a unique shareable
URL for a recipe. Returns a JSON response with the share URL.

## Why
Recipe sharing is the #1 requested feature. This endpoint is the backend
foundation that the UI share button will call.

## Acceptance Criteria
- POST /api/recipes/:id/share returns { "url": "https://.../:share_id" }
- Share IDs are URL-safe, unique, 12+ characters
- Shared recipe data is persisted (survives server restart)
- Requesting a share for an already-shared recipe returns the existing URL
- Returns 404 for non-existent recipe IDs
- Has unit tests covering happy path and error cases

## Technical Context
- **Router**: chi router, see api/routes.go for existing route registration
- **Pattern to follow**: see api/handlers/recipe.go RecipeHandler for how
  existing endpoints are structured (handler struct, ServeHTTP pattern)
- **Database**: SQLite via database/db.go, see database/migrations/ for
  schema migration pattern
- **Models**: models/recipe.go for existing Recipe struct
- **ID generation**: use crypto/rand, see utils/id.go for existing pattern

## Constraints
- Use existing SQLite database (no new storage backends)
- Share IDs must be URL-safe (base62 or similar)
- No authentication required to create shares (for now)

## Out of Scope
- The GET endpoint for viewing shared recipes (separate bead)
- UI share button (separate bead)
- Share expiration or revocation
- Analytics/tracking of share views

## Related
- Blocks: as-XXX (share viewing endpoint depends on this)
- Design: .designs/recipe-sharing/design-doc.md
BEAD
)"
```

### Step 6: Set Up Dependencies

If beads have ordering dependencies, link them:

```bash
bd update <blocker-id> --blocks <dependent-id>
```

Only add hard dependencies where one bead literally cannot start without
another being complete (e.g., "create the database table" blocks "write the
API handler that queries it"). Prefer making beads independent where possible.

### Step 7: Review and Validate

After creating all beads, review the full set:

```bash
bd list
bd show <each-id>
```

Check:

- Does each bead stand alone? Could a fresh polecat with zero context execute it?
- Are file paths accurate? (verify with `ls` or `find`)
- Are the acceptance criteria actually testable?
- Is anything missing? (common miss: forgetting to include test requirements)
- Are dependencies correct? (no circular deps, minimal blocking)

## Common Pitfalls

**Too little context**: "Add sharing feature" — useless to a polecat.

**Wrong file paths**: Referencing files that don't exist or have moved. Always
verify paths against the actual codebase before including them.

**Implicit knowledge**: "Use the standard pattern" — what standard pattern?
Point to a specific file and say "follow the pattern in handlers/recipe.go".

**Missing test expectations**: If you don't say "write tests", many polecats
won't. Be explicit about test requirements in acceptance criteria.

**Scope ambiguity**: If a polecat could reasonably interpret the bead two
different ways, it will pick the wrong one. Be specific.

**Forgetting "out of scope"**: Without explicit boundaries, polecats may
gold-plate or wander into adjacent work.

## Tips for Different Source Types

**From a design convoy**: The design doc has sections for each dimension (API,
data, UX, scale, security, integration). Pull technical context from the
relevant dimension analyses, not just the synthesis. The `api.md` will have
interface details, `data.md` will have schema details, etc.

**From a conversation**: Summarize the key decisions first. Conversations
meander — distill to: what was decided, what was explicitly ruled out, and
what constraints were identified.

**From an existing big bead**: Read the original bead, check if work has
already started (`git log`, `git branch -a`), and preserve any partial
progress context in the new beads.

**From a bug report**: Include steps to reproduce, expected vs actual behavior,
and which file/function the bug is likely in. If you can identify the root
cause, include that. A polecat debugging blind is slow.
