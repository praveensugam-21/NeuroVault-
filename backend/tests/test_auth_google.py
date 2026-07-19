import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine
from app.models.user import User
from sqlalchemy.orm import sessionmaker

# Setup test database connection
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_google_verify_invalid_token(client):
    """Verifies that an invalid ID token raises 401."""
    response = client.post("/api/auth/google/verify", json={"id_token": "invalid_mock_token"})
    assert response.status_code == 401
    assert "Google authentication failed" in response.json()["detail"]

@patch("google.oauth2.id_token.verify_oauth2_token")
def test_google_verify_success_new_user(mock_verify, client):
    """Verifies that verifying a valid Google ID token for a new user creates the account successfully."""
    mock_verify.return_value = {
        "iss": "accounts.google.com",
        "sub": "1234567890googleid",
        "email": "testgoogleuser@gmail.com",
        "email_verified": True,
        "name": "Test Google User"
    }

    db = TestingSessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == "testgoogleuser@gmail.com").first()
        if existing_user:
            db.delete(existing_user)
            db.commit()
    finally:
        db.close()

    response = client.post("/api/auth/google/verify", json={"id_token": "valid_mock_token"})
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == "testgoogleuser@gmail.com").first()
        assert user is not None
        assert user.oauth_provider == "google"
        assert user.oauth_id == "1234567890googleid"
    finally:
        db.close()

@patch("google.oauth2.id_token.verify_oauth2_token")
def test_google_verify_auto_link(mock_verify, client):
    """Verifies that verifying a valid Google ID token auto-links to an existing local account with the same email."""
    db = TestingSessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == "autolinkuser@gmail.com").first()
        if existing_user:
            db.delete(existing_user)
            db.commit()
            
        user = User(
            email="autolinkuser@gmail.com",
            hashed_password="somehashpassword",
            oauth_provider="local"
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    mock_verify.return_value = {
        "iss": "accounts.google.com",
        "sub": "9876543210googleid",
        "email": "autolinkuser@gmail.com",
        "email_verified": True
    }

    response = client.post("/api/auth/google/verify", json={"id_token": "valid_mock_token_2"})
    assert response.status_code == 200

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == "autolinkuser@gmail.com").first()
        assert user is not None
        assert user.oauth_provider == "google"
        assert user.oauth_id == "9876543210googleid"
    finally:
        db.close()
