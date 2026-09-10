import pytest
from app.validators.user_validator import validate_password_strength, validate_username, validate_email
from app.validators.labour_validator import validate_cnic, format_cnic, validate_mobile, format_mobile, validate_labour_account


def test_password_strength_valid():
    valid, errors = validate_password_strength("SecureAdmin@123")
    assert valid is True
    assert len(errors) == 0


def test_password_strength_invalid():
    valid, errors = validate_password_strength("weak")
    assert valid is False
    assert any("at least 12 characters" in e for e in errors)
    assert any("uppercase" in e for e in errors)
    assert any("number" in e for e in errors)
    assert any("special" in e for e in errors)


def test_username_validation():
    valid, _ = validate_username("admin_user")
    assert valid is True

    valid, err = validate_username("")
    assert valid is False
    assert "empty" in err

    valid, err = validate_username("ab")
    assert valid is False
    assert "3 characters" in err


def test_cnic_validation_and_formatting():
    # Valid formatted
    valid, _ = validate_cnic("35202-1234567-1")
    assert valid is True

    # Raw 13 digits
    valid, _ = validate_cnic("3520212345671")
    assert valid is True

    # Auto formatting
    formatted = format_cnic("3520212345671")
    assert formatted == "35202-1234567-1"

    # Invalid CNIC
    valid, err = validate_cnic("1234")
    assert valid is False
    assert "Invalid CNIC" in err


def test_mobile_validation_and_formatting():
    valid, _ = validate_mobile("03001234567")
    assert valid is True

    valid, _ = validate_mobile("+923001234567")
    assert valid is True

    formatted = format_mobile("923001234567")
    assert formatted == "+923001234567"

    valid, err = validate_mobile("12345")
    assert valid is False


def test_labour_account_validation():
    valid_data = {
        "WorkerID": "W-1001",
        "AccountTypeID": 1,
        "EnglishName": "Tariq Mahmood",
        "CNIC": "35202-1234567-1",
        "Mobile": "03001234567",
        "ReferenceName": "Aslam",
        "ReferenceMobile": "03007654321",
        "DailyModularTarget": 1000,
        "DailyFillerTarget": 500
    }
    valid, errors = validate_labour_account(valid_data)
    assert valid is True
    assert len(errors) == 0

    invalid_data = valid_data.copy()
    invalid_data["WorkerID"] = ""
    invalid_data["CNIC"] = "invalid"
    invalid_data["DailyModularTarget"] = -50
    valid, errors = validate_labour_account(invalid_data)
    assert valid is False
    assert len(errors) >= 3
