# Docs Index

Each folder has one responsibility. Each file covers one topic. Read only the folder you need.

| Folder | Responsibility (answers the question) |
|---|---|
| [vision/](vision/) | **Why** does this project exist and what counts as success? |
| [requirements/](requirements/) | **What** must the tutor do, and how well? |
| [pedagogy/](pedagogy/) | **How** does the tutor teach and measure learning? |
| [observation/](observation/) | **How** does the tutor watch other coding agents? |
| [architecture/](architecture/) | **How** is the tutor built (components, data, flow)? |
| [milestones/](milestones/) | **When** is what built, and when is each step done? Start at [overview](milestones/overview.md). |
| [decisions/](decisions/) | **Which** choices were made, when, and why (ADRs)? |
| [glossary/](glossary/) | **What** do our terms mean? |

## Rules
- Folders describe the **current state**. `decisions/` holds the **history**: why the current state is what it is.
- A new decision goes in a new ADR (`decisions/NNNN-title.md`). Then update the affected topic file and link back to the ADR.
- Don't edit an accepted ADR. Supersede it with a new one.
- When a file grows past one topic, split it and update this index.
