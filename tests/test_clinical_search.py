from uuid import uuid4
import pytest
from app.database.mongo_client import mongo_client
from app.services.mongo_service import mongo_service


def test_literal_search_matches_symptoms_and_paginates_every_result():
    collection = mongo_client.get_adverse_reports_collection()
    token = uuid4().hex
    ids = collection.insert_many([{'report_id': f'SEARCH-{token}-{n:02}',
        'reported_at': '2026-01-01T00:00:00+00:00', 'clinical_notes': 'Unrelated narrative',
        'symptoms': [{'name': token + ' nausea'}]} for n in range(25)]).inserted_ids
    try:
        first = mongo_service.search_clinical_reports(token)
        second = mongo_service.search_clinical_reports(token, page=2)
        assert first['total'] == second['total'] == 25
        assert len(first['items']) == 20 and len(second['items']) == 5
        assert len({r['report_id'] for r in first['items'] + second['items']}) == 25
        assert mongo_service.search_clinical_reports(token + '.*')['total'] == 0
        assert mongo_service.search_clinical_reports(token.upper())['total'] == 25
    finally:
        collection.delete_many({'_id': {'$in': ids}})


def test_search_does_not_hide_database_failures(monkeypatch):
    def fail():
        raise RuntimeError('Database unavailable')
    monkeypatch.setattr(mongo_client, 'get_adverse_reports_collection', fail)
    with pytest.raises(RuntimeError):
        mongo_service.search_clinical_reports('nausea')
