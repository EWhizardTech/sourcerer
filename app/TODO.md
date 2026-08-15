I need you to fix the HuggingFace model loading issue in my FastAPI application. The models are being downloaded repeatedly during runtime, which is inefficient and causes delays.

## Requirements

1. **Download models to repository directory** (NOT user home directory)
   - Create a `hf-models/` directory in the project root
   - Store all HuggingFace models there
   - Make it OS-agnostic (works on Windows, Linux, macOS)

2. **Pre-download models before app starts**
   - Check if models exist locally
   - If not present, download them
   - Only then start the FastAPI server

3. **Singleton pattern for model loading**
   - Load models once at application startup
   - Reuse the same model instance across all requests
   - No repeated downloads during runtime

4. **Models needed**
   - `ramsrigouthamg/t5_squad_v1` (for quiz generation)
   - Store in `hf-models/t5_squad_v1/`

## Implementation Steps

1. Create `app/services/model_manager.py`:
   - Singleton class to manage model loading
   - Method to check if model exists locally
   - Method to download model if missing
   - Property getters for model and tokenizer

2. Create `app/core/startup.py`:
   - Function to ensure models are downloaded
   - Called before FastAPI app starts

3. Update `app/main.py`:
   - Use FastAPI lifespan context manager
   - Call model initialization on startup
   - Log progress clearly

4. Update any existing quiz/generation services:
   - Use the singleton model_manager
   - Remove duplicate model loading code

5. Create `.gitignore` entry:
   - Add `hf-models/` directory to gitignore
   - Keep the directory structure but not the model files

6. Add environment variable support:
   - `HF_HUB_DISABLE_SYMLINKS_WARNING=1`
   - `TRANSFORMERS_CACHE=./models`
   - Make it work without .env file (use defaults)

## Expected Behavior

- First run: Downloads models to `./hf-models/`, then starts server
- Subsequent runs: Uses cached models, starts immediately
- No downloads during API requests
- Works identically on Windows/Linux/macOS

## File Structure After Implementation
```
sourcerer-backend/
├── app/
│   ├── services/
│   │   ├── model_manager.py (NEW)
│   │   └── quiz_service.py (UPDATE)
│   ├── core/
│   │   └── startup.py (NEW)
│   └── main.py (UPDATE)
├── hf-models/ (NEW - gitignored)
│   └── t5_squad_v1/
│       ├── config.json
│       ├── pytorch_model.bin
│       └── ...
└── .gitignore (UPDATE)
```

Please implement this solution with proper error handling and logging.
