"""Smoke checks for the new lab catalog, independent of WSO2 network access."""
from fastapi import FastAPI
from fastapi.routing import APIRoute
from demo.lab_hub import router, catalog_for, TESTS, DEFERRED


def test_hub_catalog_is_explicitly_navigation_only():
    app=FastAPI()
    @app.get('/pairwise')
    def pairwise():return 'ok'
    @app.get('/api/private-token')
    def sensitive():return 'no'
    @app.post('/api/trigger')
    def mutating():return {'ok':True}
    app.include_router(router)
    tests,other=catalog_for(app)
    assert any(t['id']=='pairwise' and t['available'] for t in tests)
    assert not any(t['id']=='m2m' and t['available'] for t in tests)
    assert not any(t['path']=='/api/private-token' for t in other)
    assert not any(t['path']=='/api/trigger' for t in other)
    assert '/lab' not in [t['path'] for t in other]
    assert len(DEFERRED)==3
    assert len(TESTS)>=20


def test_api_routes_are_get_only_and_static():
    methods={r.path:r.methods for r in router.routes if isinstance(r,APIRoute)}
    assert methods['/lab']=={'GET'}
    assert methods['/api/lab/catalog']=={'GET'}
    assert all(not t['path'].startswith('http') or t['path'].startswith('http://localhost:') for t in TESTS)
