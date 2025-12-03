import sys
import os
import io
import asyncio
import numpy as np
from PIL import Image
import torch

# Add ComfyUI to sys.path
comfy_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ComfyUI")
if comfy_path not in sys.path:
    sys.path.append(comfy_path)

# Ensure CPU mode if CUDA is not available
if not torch.cuda.is_available():
    if "--cpu" not in sys.argv:
        sys.argv.append("--cpu")

# Enable arg parsing so ComfyUI reads the --cpu flag
import comfy.options
comfy.options.enable_args_parsing()

# ComfyUI Imports
import nodes
import execution
import folder_paths

# Initialize paths
for d in ["input", "output", "temp"]:
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

class DummyServer:
    def __init__(self):
        self.client_id = "headless_worker"
        self.last_node_id = None
        self.last_prompt_id = None
        self.current_node_id = None

    def send_sync(self, event, data, sid=None):
        if event == "executing":
            self.current_node_id = data.get("node")

    def queue_updated(self):
        pass

# Global state to track initialization
_initialized = False

async def _init_nodes():
    await nodes.init_extra_nodes()

def init_comfyui():
    global _initialized
    if _initialized:
        return

    # Setup paths
    folder_paths.set_output_directory(os.path.abspath("output"))
    folder_paths.set_input_directory(os.path.abspath("input"))
    folder_paths.set_temp_directory(os.path.abspath("temp"))

    # Initialize nodes
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # If we are already in a running loop, we can't block.
        # But this function is sync. This implies misusage if called from async without await.
        # However, for this task, we assume it's called from a worker script (sync).
        # We'll use create_task if possible but we need to wait.
        # Actually, standard asyncio.run() creates a new loop.
        # If a loop is running, we can't use run_until_complete easily on it from sync code.
        # We will assume standard usage: no existing loop or we are the owner.
        # If there is a running loop, we might fail.
        # But `nodes.init_extra_nodes()` is robust enough to be called once.
        pass
    else:
        asyncio.run(_init_nodes())

    _initialized = True

def execute_workflow(workflow_json):
    """
    Executes a ComfyUI workflow and returns the generated images as raw bytes (PNG).

    Args:
        workflow_json (dict): The workflow in API format (keyed by node ID).

    Returns:
        dict: A dictionary mapping node IDs to a list of image bytes (PNG format).
    """
    init_comfyui()

    # Generate a random prompt_id
    import uuid
    prompt_id = str(uuid.uuid4())

    # Create server and executor
    server_instance = DummyServer()
    executor = execution.PromptExecutor(server_instance)

    captured_outputs = {}

    # Monkeypatch SaveImage to capture output
    original_save_images = nodes.SaveImage.save_images

    def capture_save_images(self, images, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None):
        # Process images (Tensor: B, H, W, C)
        results = []

        # Get the current executing node ID from the server
        node_id = server_instance.current_node_id

        if node_id is not None:
             if node_id not in captured_outputs:
                 captured_outputs[node_id] = []

        for batch_number, image in enumerate(images):
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_bytes = buffered.getvalue()

            if node_id is not None:
                captured_outputs[node_id].append(img_bytes)

            results.append({
                "filename": "captured.png",
                "subfolder": "",
                "type": "output"
            })

        return { "ui": { "images": results } }

    # Apply patch
    nodes.SaveImage.save_images = capture_save_images
    # Also patch PreviewImage just in case, though it usually inherits
    nodes.PreviewImage.save_images = capture_save_images

    try:
        # Execute
        executor.execute(workflow_json, prompt_id, extra_data={})
    finally:
        # Restore patch
        nodes.SaveImage.save_images = original_save_images
        nodes.PreviewImage.save_images = original_save_images

    return captured_outputs
