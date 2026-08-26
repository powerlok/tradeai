from app.services.operational_state import entry_enabled


def test_paper_and_testnet_allow_entries():
    assert entry_enabled("PAPER") is True
    assert entry_enabled("testnet") is True


def test_disabled_states_block_entries():
    assert entry_enabled("LIVE_DISABLED") is False
    assert entry_enabled("KILL_SWITCH") is False