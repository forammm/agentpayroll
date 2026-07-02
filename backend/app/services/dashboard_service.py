from uuid import UUID


def get_mock_summary(user_id: UUID) -> dict:
    return {"user_id": user_id, "expected_pay": 1842.50, "actual_pay": 1745.20, "difference": -97.30, "hours_logged": 76.5, "status": "underpaid"}
