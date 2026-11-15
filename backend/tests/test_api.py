from fastapi.testclient import TestClient


def test_report_endpoint_serializes_money_as_strings(client: TestClient) -> None:
    response = client.get("/api/report", params={"report_date": "2026-11-10"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_date"] == "2026-11-10"
    assert payload["totals"] == {
        "contract_amount": "690000.00",
        "active_works_amount": "590000.00",
        "paid": "390000.00",
        "remaining": "200000.00",
        "unallocated": "0.00",
    }
    assert payload["contracts"][1]["works"][2] == {
        "work_id": "W-23",
        "title": "Упаковка",
        "status": "planned",
        "price": "40000.00",
        "paid": "25000.00",
        "remaining": "15000.00",
    }


def test_report_date_is_required_and_validated(client: TestClient) -> None:
    assert client.get("/api/report").status_code == 422
    assert (
        client.get("/api/report", params={"report_date": "10.11.2026"}).status_code
        == 422
    )


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
