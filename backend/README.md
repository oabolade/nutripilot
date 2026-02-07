# NutriPilot AI Backend

FastAPI backend for NutriPilot AI - an autonomous nutrition agent with Observe-Think-Act architecture.

## Features

- 🔍 **Observe**: Analyze food images with Gemini 2.0 Flash Vision
- 🧠 **Think**: Process health constraints and lookup nutrition data
- ⚡ **Act**: Generate personalized meal recommendations
- 📊 **Tracing**: Full observability with Comet Opik integration

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API keys
```

### 3. Run the Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --port 8000

# Or run directly
python -m app.main
```

### 4. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Analyze a meal (text)
curl -X POST http://localhost:8000/analyze \
  -F "text_input=grilled chicken with rice and vegetables" \
  -F "user_id=demo_user"

# Analyze a meal (image)
curl -X POST http://localhost:8000/analyze \
  -F "image=@path/to/food_image.jpg" \
  -F "user_id=demo_user"
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check with API key status |
| `/analyze` | POST | Analyze meal from image or text |
| `/docs` | GET | Interactive API documentation (Swagger UI) |

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings management
│   └── core/
│       ├── __init__.py
│       ├── state.py         # Pydantic models (MealState, FoodItem, etc.)
│       ├── base_agent.py    # Abstract agent class
│       └── orchestrator.py  # Observe-Think-Act pipeline
├── pyproject.toml           # Project dependencies
├── .env.example             # Environment variables template
└── README.md
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_GENERATIVE_AI_API_KEY` | Yes | Gemini API key for vision analysis |
| `OPIK_API_KEY` | No | Comet Opik key for observability |
| `USDA_API_KEY` | No | USDA FoodData Central key (Phase 4) |
| `OPIK_PROJECT_NAME` | No | Opik project name (default: nutripilot) |
| `DEBUG` | No | Enable debug mode (default: true) |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black app/
ruff check app/ --fix
```

## Architecture

The backend implements the **Observe-Think-Act** pattern:

```
┌─────────────────────────────────────────────────────────────────┐
│                      StudioOrchestrator                         │
├─────────────────────────────────────────────────────────────────┤
│  1. OBSERVE          2. THINK              3. ACT               │
│  ─────────          ───────              ────                   │
│  • Image analysis   • Health constraints  • Adjustments         │
│  • Food detection   • Nutrition lookup    • Meal scoring        │
│  • Portion est.     • Violation check     • Summary             │
└─────────────────────────────────────────────────────────────────┘
```

## License

MIT
