"""Campaign templates: common task sequences with editable effort ranges.

Each step may name prerequisites by `key`. Effort is in hours (min, max).
`due_offset_days` moves a step's deadline earlier than the campaign deadline
(e.g. -3 means three days before); steps inherit the campaign deadline
otherwise. Steps with `review: True` offer a "request changes" action that
creates a revision task and a fresh review gate instead of reopening work.
"""

TEMPLATES = {
    "video": {
        "label": "Client video",
        "steps": [
            {"key": "script", "name": "Scriptwriting", "kind": "task", "skill": "writing",
             "effort": (2, 4), "due_offset_days": -4},
            {"key": "script_ok", "name": "Script approval", "kind": "gate",
             "prereqs": ["script"]},
            {"key": "film", "name": "Filming", "kind": "gate", "prereqs": ["script_ok"]},
            {"key": "edit", "name": "Editing", "kind": "task", "skill": "editing",
             "effort": (3, 6), "prereqs": ["film"], "due_offset_days": -1},
            {"key": "review", "name": "Client review", "kind": "gate", "prereqs": ["edit"],
             "review": True, "revision_skill": "editing", "revision_effort": (1, 2)},
            {"key": "final", "name": "Final approval", "kind": "gate", "prereqs": ["review"]},
        ],
    },
    "social": {
        "label": "Social media set",
        "steps": [
            {"key": "copy", "name": "Caption copywriting", "kind": "task", "skill": "writing",
             "effort": (1, 2), "due_offset_days": -2},
            {"key": "assets", "name": "Graphic/video cut-downs", "kind": "task",
             "skill": "editing", "effort": (2, 3), "due_offset_days": -2},
            {"key": "review", "name": "Client review", "kind": "gate",
             "prereqs": ["copy", "assets"], "review": True,
             "revision_skill": "editing", "revision_effort": (0.5, 1)},
            {"key": "final", "name": "Final approval", "kind": "gate", "prereqs": ["review"]},
        ],
    },
    "article": {
        "label": "Blog article",
        "steps": [
            {"key": "draft", "name": "Article draft", "kind": "task", "skill": "writing",
             "effort": (3, 5), "due_offset_days": -2},
            {"key": "proof", "name": "Copy edit & layout", "kind": "task", "skill": "editing",
             "effort": (1, 2), "prereqs": ["draft"], "due_offset_days": -1},
            {"key": "review", "name": "Client review", "kind": "gate", "prereqs": ["proof"],
             "review": True, "revision_skill": "writing", "revision_effort": (1, 2)},
        ],
    },
}
