# 0007: On-demand tutor pane plus background detection with desktop notifications

- **Status:** Accepted
- **Date:** 2026-11-12

## Context
Live interruptions while an agent works are distracting. Waiting until I happen to ask means I miss concepts. I want to learn when I choose to, but without missing what came up.

## Decision
- **Background detection:** a Claude Code hook triggers concept detection. New, worth-knowing concepts are added to the memory as `new`.
- **Notification:** a desktop notification tells me a new concept was found. It does not appear inside the agent's session.
- **On-demand learning:** a tutor TUI runs in a separate terminal pane. There I browse the queue of new concepts, open lessons, and ask about the current session.

## Alternatives considered
- Live teaching inside the agent session: the most timely, but it interrupts the work and pollutes the agent's context.
- Only a debrief after each session: less distraction, but the lessons arrive long after the moment.
- A web app or Obsidian as the interface: more UI work, or out of the terminal workflow I use.

## Consequences
- The agent session is never blocked or changed by the tutor.
- I need a desktop notification daemon on Linux (`notify-send`).
- Updated: [requirements/functional.md](../requirements/functional.md), [observation/triggers.md](../observation/triggers.md), [architecture/overview.md](../architecture/overview.md).
