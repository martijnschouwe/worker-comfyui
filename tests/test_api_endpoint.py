import sys
import os
import json
import base64
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Add src to path to import app
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(os.path.dirname(current_dir), "src")
repo_root = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.append(src_dir)
if repo_root not in sys.path:
    sys.path.append(repo_root)

# Mock worker_logic before importing app
# We need to mock it in sys.modules so app.py picks up the mock
mock_worker_logic = MagicMock()
sys.modules["worker_logic"] = mock_worker_logic

from app import app

client = TestClient(app)

def test_generate_success():
    # Setup mock return value
    # execute_workflow returns dict[node_id, list[bytes]]
    fake_image_bytes = b"fake_image_data"
    mock_worker_logic.execute_workflow.return_value = {
        "9": [fake_image_bytes]
    }

    workflow_payload = {
        "workflow": {
            "3": {"class_type": "KSampler"},
            "9": {"class_type": "SaveImage"}
        }
    }

    response = client.post("/generate", json=workflow_payload)

    assert response.status_code == 200
    data = response.json()
    assert "images" in data
    assert len(data["images"]) == 1
    assert data["images"][0]["node_id"] == "9"
    # Base64 of b"fake_image_data" is "ZmFrZV9pbWFnZV9kYXRh"
    expected_b64 = base64.b64encode(fake_image_bytes).decode("utf-8")
    assert data["images"][0]["data"] == expected_b64

def test_generate_validation_error():
    # Setup mock to raise ValueError
    mock_worker_logic.execute_workflow.side_effect = ValueError("Invalid node connection")

    workflow_payload = {
        "workflow": {}
    }

    response = client.post("/generate", json=workflow_payload)

    assert response.status_code == 400
    assert "Invalid node connection" in response.json()["detail"]

def test_generate_server_error():
    # Setup mock to raise generic Exception
    mock_worker_logic.execute_workflow.side_effect = RuntimeError("OOM Error")

    workflow_payload = {
        "workflow": {}
    }

    response = client.post("/generate", json=workflow_payload)

    assert response.status_code == 500
    assert "Execution failed: OOM Error" in response.json()["detail"]
