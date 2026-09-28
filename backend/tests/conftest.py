import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ.setdefault("ARAP_DATABASE_URL", f"sqlite:///{_tmp}/test.db")
os.environ.setdefault("ARAP_SEED_DEMO", "true")


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app
    with TestClient(app) as c:
        yield c


def token(client, user, pw):
    r = client.post("/api/auth/login", data={"username": user, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin(client):
    return token(client, "admin", "admin")


@pytest.fixture(scope="session")
def assessor(client):
    return token(client, "assessor", "demo1234")


@pytest.fixture(scope="session")
def reviewer(client):
    return token(client, "reviewer", "demo1234")


@pytest.fixture(scope="session")
def director(client):
    return token(client, "director", "demo1234")


@pytest.fixture(scope="session")
def accexec(client):
    return token(client, "accexec", "demo1234")


@pytest.fixture(scope="session")
def viewer(client):
    return token(client, "viewer", "demo1234")
