"""What the tutor pane lists (ADR 0035): pure functions, no Textual."""

from tutor_agent import browse
from tutor_agent.browse import Filters, Sort
from tutor_agent.store import Concept, Source, Status


def concept(
    name: str,
    status: Status = Status.NEW,
    *,
    category: str = "Mechanisms",
    project: str | None = "/home/me/Projects/api/",
    created: str = "2026-11-01",
    sources: int = 1,
    summary: str = "",
) -> Concept:
    return Concept(
        id=name.lower(),
        name=name,
        category=category,
        summary=summary,
        status=status,
        created_at=created,
        sources=[Source(snippet="x", context="c", project=project) for _ in range(sources)],
    )


def names(concepts: list[Concept]) -> list[str]:
    return [c.name for c in concepts]


def test_fuzzy_matches_letters_in_order_ignoring_case_and_spaces():
    assert browse.fuzzy("flk", "File locking")
    assert browse.fuzzy("file lock", "File locking")
    assert browse.fuzzy("", "anything")
    assert not browse.fuzzy("klf", "File locking")


def test_matches_name_fuzzily_or_summary_by_substring():
    c = concept("Worker threads", summary="Keeps the UI responsive.")
    assert browse.matches(c, Filters(query="wkth"))
    assert browse.matches(c, Filters(query="ui RESPONSIVE"))
    assert not browse.matches(c, Filters(query="zzz"))
    assert browse.matches(c, Filters(query="   "))  # blank is no search


def test_project_and_category_filters():
    c = concept("A", category="Patterns", project="/p/web")
    assert browse.matches(c, Filters(project="web", category="Patterns"))
    assert not browse.matches(c, Filters(project="api"))
    assert not browse.matches(c, Filters(category="Mechanisms"))
    assert browse.project_name(concept("B", project=None)) == "?"
    assert browse.project_name(concept("C", project="/p/api/")) == "api"


def test_sort_orders():
    cs = [
        concept("Beta", created="2026-11-02", sources=3),
        concept("alpha", created="2026-11-01", sources=1),
        concept("Gamma", created="2026-11-03", sources=3),
    ]
    assert names(browse.sort(cs, Sort.NEWEST)) == ["Gamma", "Beta", "alpha"]
    assert names(browse.sort(cs, Sort.OLDEST)) == ["alpha", "Beta", "Gamma"]
    assert names(browse.sort(cs, Sort.MOST_SEEN)) == ["Beta", "Gamma", "alpha"]  # ties by name
    assert names(browse.sort(cs, Sort.NAME)) == ["alpha", "Beta", "Gamma"]


def test_visible_and_counts_per_tab():
    cs = [
        concept("A"),
        concept("B", Status.SEEN, category="Patterns"),
        concept("C", Status.DISMISSED),
    ]
    assert names(browse.visible(cs, Status.NEW, Filters())) == ["A"]
    assert sorted(names(browse.visible(cs, None, Filters()))) == ["A", "B", "C"]
    counts = browse.counts(cs, Filters(category="Mechanisms"))
    assert counts == {
        Status.NEW: 1,
        Status.SEEN: 0,
        Status.UNDERSTOOD: 0,
        Status.DISMISSED: 1,
        None: 2,
    }


def test_filters_active_chips_and_sort_cycle():
    assert not Filters().active
    f = Filters(query="lock", project="api", category="Mechanisms")
    assert f.active
    assert f.chips() == "/ lock · project: api · category: Mechanisms · sort: newest"
    sorts = [Filters().sort]
    g = Filters()
    for _ in Sort:
        g = g.next_sort()
        sorts.append(g.sort)
    assert sorts == [*Sort, Sort.NEWEST]


def test_tab_names_and_choices():
    assert [browse.tab_title(t) for t in browse.TABS] == [
        "New",
        "Seen",
        "Understood",
        "Dismissed",
        "All",
    ]
    assert browse.tab_id(None) == "tab-all" and browse.tab_id(Status.NEW) == "tab-new"
    cs = [
        concept("A", category="b", project="/p/Web"),
        concept("B", category="A", project="/p/api"),
    ]
    assert browse.projects(cs) == ["api", "Web"]
    assert browse.categories(cs) == ["A", "b"]
