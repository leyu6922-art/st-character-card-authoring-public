from __future__ import annotations


def test_shared_matcher_honors_enabled_constant_and_secondary_logic(load_script_module):
    matcher = load_script_module("lib/worldbook_matcher.py")
    entry = {
        "keys": ["alpha"],
        "secondary_keys": ["beta"],
        "constant": False,
        "enabled": True,
        "selective": True,
        "selectiveLogic": 0,
        "extensions": {"case_sensitive": False, "match_whole_words": False},
    }

    assert matcher.entry_trigger_match(entry, "alpha beta").ok
    assert not matcher.entry_trigger_match(entry, "alpha only").ok
    assert not matcher.entry_trigger_match({**entry, "enabled": False}, "alpha beta").ok
    assert not matcher.entry_trigger_match({**entry, "constant": True}, "alpha beta").ok


def test_shared_matcher_supports_regex_and_whole_word_rules(load_script_module):
    matcher = load_script_module("lib/worldbook_matcher.py")
    regex_entry = {
        "keys": [r"/cat\d+/i"],
        "secondary_keys": [],
        "constant": False,
        "enabled": True,
        "selective": False,
        "extensions": {"case_sensitive": False, "match_whole_words": False},
    }
    whole_word_entry = {
        "keys": ["cat"],
        "secondary_keys": [],
        "constant": False,
        "enabled": True,
        "selective": False,
        "extensions": {"case_sensitive": False, "match_whole_words": True},
    }

    assert matcher.entry_trigger_match(regex_entry, "CAT42").ok
    assert matcher.entry_trigger_match(whole_word_entry, "a cat sleeps").ok
    assert not matcher.entry_trigger_match(whole_word_entry, "concatenate").ok


def test_recursive_simulation_uses_same_enabled_and_selective_rules(load_script_module):
    matcher = load_script_module("lib/worldbook_matcher.py")
    entries = [
        {
            "id": "disabled",
            "keys": ["opening"],
            "secondary_keys": [],
            "constant": False,
            "enabled": False,
            "selective": False,
            "content": "should never load",
            "extensions": {"prevent_recursion": False},
        },
        {
            "id": "selective-missing-secondary",
            "keys": ["opening"],
            "secondary_keys": ["scope"],
            "constant": False,
            "enabled": True,
            "selective": True,
            "content": "should not load without scope",
            "extensions": {"prevent_recursion": False},
        },
        {
            "id": "initial",
            "keys": ["opening"],
            "secondary_keys": [],
            "constant": False,
            "enabled": True,
            "selective": False,
            "content": "child-token",
            "extensions": {"prevent_recursion": False},
        },
        {
            "id": "recursive-child",
            "keys": ["child-token"],
            "secondary_keys": [],
            "constant": False,
            "enabled": True,
            "selective": False,
            "content": "child body",
            "extensions": {"prevent_recursion": False},
        },
    ]

    initial_ids, activated_ids = matcher.simulate_recursive_activation(entries, "opening")

    assert initial_ids == {"initial"}
    assert activated_ids == {"initial", "recursive-child"}


def test_shared_matcher_honors_st_zero_scan_depth_guard(load_script_module):
    matcher = load_script_module("lib/worldbook_matcher.py")
    entry = {
        "keys": ["玄空腾"],
        "secondary_keys": [],
        "constant": False,
        "enabled": True,
        "selective": False,
        "extensions": {"scan_depth": 0, "case_sensitive": False, "match_whole_words": False},
    }

    assert not matcher.entry_trigger_match(entry, "开场白里出现玄空腾").ok
    assert matcher.entry_trigger_match(
        {**entry, "extensions": {**entry["extensions"], "scan_depth": None}},
        "开场白里出现玄空腾",
    ).ok
