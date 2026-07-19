"""
Shared pytest fixtures for NeuroVault backend tests.
Uses an in-process SQLite database (no Docker/PostgreSQL required).
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Ensure the backend package root is importable when tests run from /backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force SQLite in-process database for all tests (no PostgreSQL needed)
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_iris.db")
os.environ.setdefault("ENCRYPTION_KEY", "AjX67sdIPJ6i7e5q_gaJBzFWASjELpKJanrbhfNs7P8=")

# ── Pre-mock optional heavy dependencies before app.main is imported ──────────
# This prevents ImportError when google-genai, ollama, or sentence-transformers
# are not installed in the local dev environment (they run in Docker instead).
import types as _types

# google.genai mock
_google_mock = MagicMock()
_genai_mock = MagicMock()
_genai_types_mock = MagicMock()
_genai_mock.types = _genai_types_mock
_genai_mock.Client = MagicMock(return_value=MagicMock())
_google_mock.genai = _genai_mock
sys.modules.setdefault("google", _google_mock)
sys.modules.setdefault("google.genai", _genai_mock)
sys.modules.setdefault("google.genai.types", _genai_types_mock)

# chromadb mock with proper submodule structure
_chromadb_mock = MagicMock()
_chromadb_config_mock = MagicMock()
_chromadb_config_mock.Settings = MagicMock
_chromadb_mock.config = _chromadb_config_mock
_chromadb_mock.PersistentClient = MagicMock(return_value=MagicMock())
sys.modules.setdefault("chromadb", _chromadb_mock)
sys.modules.setdefault("chromadb.config", _chromadb_config_mock)

# sentence_transformers mock
_st_mock = MagicMock()
_st_mock.SentenceTransformer = MagicMock()
_st_mock.CrossEncoder = MagicMock()
sys.modules.setdefault("sentence_transformers", _st_mock)

# Other optional dependencies
sys.modules.setdefault("spacy", MagicMock())
sys.modules.setdefault("cv2", MagicMock())
sys.modules.setdefault("ollama", MagicMock())

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base
from app.main import app
from app.database import get_db

# ── Test Database Setup ───────────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite:///./test_iris.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create all tables once when the test session starts
Base.metadata.create_all(bind=test_engine)


def override_get_db():
    """Override FastAPI dependency to use the test SQLite database."""
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def mock_external_services():
    """Mock Ollama and Gemini availability to ensure tests run offline and fast."""
    # Import after pre-mocking above so these work safely
    import importlib
    import app.services.gemini_service as gs
    import app.services.ollama_service as os_
    with patch.object(gs.GeminiService, "is_available", return_value=False), \
         patch.object(os_.OllamaService, "is_available", return_value=False):
        yield


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def db():
    """Session-scoped database session for direct DB assertions."""
    db = TestingSession()
    yield db
    db.close()


@pytest.fixture(scope="module")
def client():
    """Module-scoped FastAPI test client."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_headers(client):
    """
    Register a test user, login, and return the Authorization headers.
    The test user is created if it doesn't already exist.
    """
    import uuid
    test_email = f"testuser_{uuid.uuid4().hex[:8]}@test.com"
    test_password = "TestPassword123!"

    # Register
    client.post("/api/auth/register", json={"email": test_email, "password": test_password})

    # Login
    from fastapi.encoders import jsonable_encoder
    response = client.post(
        "/api/auth/login",
        data={"username": test_email, "password": test_password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
