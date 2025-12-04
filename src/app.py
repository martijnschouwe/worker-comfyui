import sys
import os
import base64
import logging
import uuid
import datetime
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from google.cloud import storage

# Add repository root to sys.path to import worker_logic
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(current_dir)
if repo_root not in sys.path:
    sys.path.append(repo_root)

try:
    import worker_logic
except ImportError as e:
    # This might happen if ComfyUI dependencies are missing in the env,
    # but we should try to import it.
    logging.error(f"Failed to import worker_logic: {e}")
    worker_logic = None

app = FastAPI()

class GenerateRequest(BaseModel):
    workflow: Dict[str, Any]

class ImageResponse(BaseModel):
    node_id: str
    data: str  # Base64 encoded image
    url: Optional[str] = None

class GenerateResponse(BaseModel):
    images: List[ImageResponse]

@app.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    if not worker_logic:
        raise HTTPException(status_code=500, detail="Worker logic module not loaded.")

    bucket_name = os.environ.get("GCS_BUCKET_NAME")

    try:
        # Run the workflow
        # worker_logic.execute_workflow expects the workflow dictionary
        outputs = worker_logic.execute_workflow(request.workflow)

        response_images = []

        storage_client = None
        bucket = None
        if bucket_name:
             storage_client = storage.Client()
             bucket = storage_client.bucket(bucket_name)

        for node_id, image_list in outputs.items():
            for img_bytes in image_list:
                b64_encoded = base64.b64encode(img_bytes).decode('utf-8')
                image_response = ImageResponse(node_id=str(node_id), data=b64_encoded)

                if bucket:
                    try:
                        blob_name = f"output_{uuid.uuid4()}.png"
                        blob = bucket.blob(blob_name)
                        blob.upload_from_string(img_bytes, content_type="image/png")

                        url = blob.generate_signed_url(
                            version="v4",
                            expiration=datetime.timedelta(hours=24),
                            method="GET"
                        )
                        image_response.url = url
                    except Exception as e:
                         logging.error(f"Failed to upload to GCS: {e}")
                         raise Exception(f"Failed to upload to GCS: {str(e)}")

                response_images.append(image_response)

        return GenerateResponse(images=response_images)

    except ValueError as ve:
        # Assuming ValueError is raised for invalid inputs (e.g. bad node format)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Execution failed: {e}")
        # Return 500 for other errors (OOM, internal crashes)
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")
