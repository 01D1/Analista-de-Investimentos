from src.options.expiration_engine import (
    calculate_option_expiration_value,
    calculate_structure_expiration_value,
    handle_expired_structure,
)


def test_option_expiration_values_call_put():
    assert calculate_option_expiration_value("CALL", 35, 30) == 5
    assert calculate_option_expiration_value("PUT", 25, 30) == 5
    assert calculate_option_expiration_value("CALL", 25, 30) == 0


def test_structure_expiration_value_and_handler():
    structure = {
        "legs": [{"option_type": "CALL", "direction": "BUY", "strike": 30, "quantity": 1}],
        "entry_debit": 100,
    }
    assert calculate_structure_expiration_value(structure, 35) == 500
    result = handle_expired_structure(structure, 35)
    assert result["has_intrinsic_value"] is True
    assert result["pnl_at_expiry"] == 400

