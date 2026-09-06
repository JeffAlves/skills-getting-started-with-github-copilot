from copy import deepcopy
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def restore_activities():
    original_participants = {
        name: deepcopy(activity["participants"])
        for name, activity in activities.items()
    }

    yield

    for name, participants in original_participants.items():
        activities[name]["participants"] = participants


def test_get_activities_returns_activity_mapping(client):
    # Arrange
    expected_activity = "Chess Club"

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert expected_activity in response.json()
    assert {"description", "schedule", "max_participants", "participants"}.issubset(
        response.json()[expected_activity]
    )


def test_root_redirects_to_static_index(client):
    # Arrange
    client = TestClient(app, follow_redirects=False)

    # Act
    response = client.get("/")

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_signup_adds_participant(client):
    # Arrange
    activity_name = "Soccer Club"
    email = "new.student@mergington.edu"

    # Act
    response = client.post(
        f"/activities/{quote(activity_name, safe='')}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 200
    assert email in activities[activity_name]["participants"]
    assert response.json() == {
        "message": f"Signed up {email} for {activity_name}"
    }


def test_signup_rejects_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"
    email = "student@mergington.edu"

    # Act
    response = client.post(
        f"/activities/{quote(activity_name, safe='')}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_rejects_duplicate_participant(client):
    # Arrange
    activity_name = "Chess Club"
    email = activities[activity_name]["participants"][0]
    original_count = activities[activity_name]["participants"].count(email)

    # Act
    response = client.post(
        f"/activities/{quote(activity_name, safe='')}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"
    assert activities[activity_name]["participants"].count(email) == original_count


def test_signup_requires_email(client):
    # Arrange
    activity_name = "Chess Club"

    # Act
    response = client.post(
        f"/activities/{quote(activity_name, safe='')}/signup"
    )

    # Assert
    assert response.status_code == 422


def test_remove_participant_supports_url_encoded_email(client):
    # Arrange
    activity_name = "Soccer Club"
    email = "student+art@mergington.edu"
    activities[activity_name]["participants"].append(email)

    # Act
    response = client.delete(
        f"/activities/{quote(activity_name, safe='')}/participants/"
        f"{quote(email, safe='')}"
    )

    # Assert
    assert response.status_code == 200
    assert email not in activities[activity_name]["participants"]
    assert response.json() == {
        "message": f"Removed {email} from {activity_name}"
    }


def test_remove_participant_rejects_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"
    email = "student@mergington.edu"

    # Act
    response = client.delete(
        f"/activities/{quote(activity_name, safe='')}/participants/"
        f"{quote(email, safe='')}"
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_remove_participant_rejects_unknown_participant(client):
    # Arrange
    activity_name = "Soccer Club"
    email = "missing@mergington.edu"

    # Act
    response = client.delete(
        f"/activities/{quote(activity_name, safe='')}/participants/"
        f"{quote(email, safe='')}"
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Participant not found"
