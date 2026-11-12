# M6: Daily Use and Tuning

> **Responsibility:** Run the tutor in real daily work, tune it, and check it against the goals.

## Goal
The tutor runs in all my sessions for two weeks, and I fix whatever stops it from being useful.

## Scope
- Keep a short issue log during use: missed concepts, noise, bad lessons, slow spots, crashes.
- Tune the detection and lesson prompts against that log. Switch the detection model if quality is too low ([0016](../decisions/0016-model-per-job.md)).
- Check the size of the concept memory and the usage per day.
- Record lasting design changes as ADRs.

## Done when
- [ ] Two weeks of use with no tutor problem ever showing up in an agent session.
- [ ] Notifications feel useful, not noisy (most detected concepts are ones I want to learn).
- [ ] Each [goal](../vision/goals.md) is reviewed: what works and what's missing.
- [ ] The next round of work (for example quizzes or a project filter) is listed as candidate ADRs.
