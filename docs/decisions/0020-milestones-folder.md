# 0020: Add a `milestones/` folder to the docs

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
The design phase is done and implementation is planned in milestones. [0001](0001-docs-structure.md) defined the docs folders, but none of them answers "in what order is it built, and when is a step done?".

## Decision
- Add `docs/milestones/`, which answers **when**: the order of the work and each milestone's "done when" criteria.
- `overview.md` lists the milestones, their dependencies, and which requirements each one delivers. Each milestone has its own file.
- Milestone files plan work. Design changes found during a milestone are still recorded as ADRs and in the topic folders.

## Alternatives considered
- GitHub issues or a project board: good for tracking, but the plan would live outside the docs that agents load as context.
- One `roadmap.md` file: breaks the one-topic-per-file rule once milestones get detailed.

## Consequences
- An agent working on a milestone can load just that file plus the docs it links to.
- Checkboxes in the milestone files need to be kept up to date as work finishes.
- Updated: `docs/CLAUDE.md`, root `CLAUDE.md`.
