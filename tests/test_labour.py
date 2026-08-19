import pytest
from app.database.init_db import init_db
from app.services.auth_service import AuthService
from app.services.labour_service import LabourService


@pytest.fixture(autouse=True)
def setup_db_and_auth():
    from app.database.schema import Base
    from app.database.connection import get_engine
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    init_db()
    # Authenticate as admin by default
    AuthService.authenticate("admin", "Admin@123")
    yield
    AuthService.logout()



def test_labour_account_creation_and_search():
    data = {
        "WorkerID": "TEST-W01",
        "AccountTypeID": 1,  # Pathera
        "EnglishName": "Muhammad Ali",
        "UrduName": "محمد علی",
        "FatherName": "Asghar",
        "CNIC": "35202-9999999-1",
        "Mobile": "03001112233",
        "ReferenceName": "Zubair",
        "ReferenceMobile": "03004445566",
        "DailyModularTarget": 1500,
        "DailyFillerTarget": 800
    }

    success, msg = LabourService.save_account(data, is_edit_mode=False)
    assert success is True
    assert "saved successfully" in msg

    # Search for account
    results = LabourService.search_accounts(query_str="Muhammad Ali")
    assert len(results) >= 1
    assert results[0]["WorkerID"] == "TEST-W01"


def test_omit_account_feature():
    worker_id = "TEST-W01"
    # Ensure account exists or create it
    if not LabourService.get_account_by_id(worker_id):
        LabourService.save_account({
            "WorkerID": worker_id,
            "AccountTypeID": 1,
            "EnglishName": "Muhammad Ali",
            "CNIC": "35202-9999999-1",
            "Mobile": "03001112233",
            "ReferenceName": "Zubair",
            "ReferenceMobile": "03004445566"
        })

    # Omit account
    success, msg = LabourService.omit_account(worker_id, "Worker left kiln for winter season")
    assert success is True
    assert "omitted" in msg

    # Search active (should be hidden)
    active_results = LabourService.search_accounts(query_str="TEST-W01", show_omitted=False)
    assert len(active_results) == 0

    # Search showing omitted (should appear)
    all_results = LabourService.search_accounts(query_str="TEST-W01", show_omitted=True)
    assert len(all_results) == 1
    assert all_results[0]["IsOmitted"] is True
    assert "left kiln" in all_results[0]["OmitReason"]


def test_munshi_delete_permission_denied():
    # Switch session to Munshi
    AuthService.logout()
    AuthService.authenticate("munshi", "Munshi@123")

    success, msg = LabourService.delete_account("TEST-W01")
    assert success is False
    assert "Munshi role is not permitted" in msg
