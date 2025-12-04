import sys
import os
import base64
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

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

class GenerateResponse(BaseModel):
    images: List[ImageResponse]

@app.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    if not worker_logic:
        raise HTTPException(status_code=500, detail="Worker logic module not loaded.")

    try:
        # Run the workflow
        # worker_logic.execute_workflow expects the workflow dictionary
        outputs = worker_logic.execute_workflow(request.workflow)

        response_images = []
        for node_id, image_list in outputs.items():
            for img_bytes in image_list:
                b64_encoded = base64.b64encode(img_bytes).decode('utf-8')
                response_images.append(ImageResponse(node_id=str(node_id), data=b64_encoded))

        return GenerateResponse(images=response_images)

    except ValueError as ve:
        # Assuming ValueError is raised for invalid inputs (e.g. bad node format)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Execution failed: {e}")
        # Return 500 for other errors (OOM, internal crashes)
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")
