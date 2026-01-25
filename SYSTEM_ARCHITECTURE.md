# NutriPilot AI - System Architecture

> **Version**: 1.0 (Hackathon MVP)
> **Author**: Lead AI Architect
> **Last Updated**: January 2026

---

## High-Level Architecture

```mermaid
flowchart TB
    subgraph Client["🌐 Client Layer"]
        FE[Next.js Frontend<br/>Vercel Hosted]
        Mobile[Future: Mobile App]
    end

    subgraph API["⚡ API Layer"]
        FastAPI[FastAPI Server<br/>Cloud Run]
    end

    subgraph Core["🧠 Core Engine"]
        Orch[StudioOrchestrator]
        State[MealState Manager]
    end

    subgraph Agents["🤖 Agent Layer"]
        VA[VisionAnalyst<br/>Gemini 2.0 Flash]
        BDS[BioDataScout<br/>Health Constraints]
        NA[NutriAuditor<br/>Nutrition Validator]
    end

    subgraph Tools["🔧 Tool Layer"]
        USDA[USDA FoodData<br/>Central API]
        HK[HealthKit Mock<br/>User Health Data]
    end

    subgraph Eval["📊 Evaluation Layer"]
        Opik[Comet Opik<br/>Observability]
        Pycalib[Pycalib<br/>Confidence Calibration]
    end

    subgraph LLM["🔮 LLM Provider"]
        Gemini[Google Gemini API<br/>Flash + Pro]
    end

    FE --> FastAPI
    Mobile -.-> FastAPI
    FastAPI --> Orch
    Orch --> State
    Orch --> VA & BDS & NA
    VA --> Gemini
    NA --> USDA
    BDS --> HK
    Orch --> Opik
    VA --> Pycalib
```

---

## Component Deep Dive

### 1. Client Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | Next.js 14, React, Tailwind | User interface for image upload and result display |
| **Hosting** | Vercel | Edge deployment, automatic HTTPS |

**Key Features:**
- Drag-and-drop image upload
- Real-time analysis progress indicator
- Interactive meal breakdown visualization
- Health constraint alerts

---

### 2. API Layer

```mermaid
flowchart LR
    subgraph Endpoints
        E1["POST /analyze"]
        E2["GET /user/{id}/state"]
        E3["GET /user/{id}/history"]
        E4["GET /health"]
    end
    
    subgraph Middleware
        CORS[CORS Handler]
        Auth[API Key Auth]
        Rate[Rate Limiter]
    end
    
    Client --> CORS --> Auth --> Rate --> Endpoints
```

**Endpoint Details:**

| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/analyze` | POST | `multipart/form-data` (image, user_id, meal_type) | `MealState` |
| `/user/{id}/state` | GET | Path param | Current `MealState` |
| `/user/{id}/history` | GET | Path param, query params | `List[MealState]` |
| `/health` | GET | - | `{"status": "ok"}` |

---

### 3. Core Engine

#### StudioOrchestrator

The central coordinator implementing the **Observe-Think-Act** pattern:

```mermaid
stateDiagram-v2
    [*] --> Observe
    
    state Observe {
        [*] --> ReceiveInput
        ReceiveInput --> VisionAnalysis: Image provided
        ReceiveInput --> OCRExtraction: Receipt/Menu
        VisionAnalysis --> DetectedFoods
        OCRExtraction --> DetectedFoods
    }
    
    Observe --> Think
    
    state Think {
        [*] --> QueryBioData
        QueryBioData --> CheckConstraints
        CheckConstraints --> LookupNutrition
        LookupNutrition --> CalculateTotals
        CalculateTotals --> IdentifyViolations
    }
    
    Think --> Act
    
    state Act {
        [*] --> GenerateAdjustments
        GenerateAdjustments --> CreateSummary
        CreateSummary --> ScoreMeal
        ScoreMeal --> UpdateState
    }
    
    Act --> [*]
```

#### MealState Lifecycle

```mermaid
flowchart LR
    subgraph Creation
        A[New Session] --> B[Initialize MealState]
    end
    
    subgraph Observe
        B --> C[Add detected_foods]
        C --> D[Set image_analysis_confidence]
    end
    
    subgraph Think
        D --> E[Add health_constraints]
        E --> F[Calculate total_nutrients]
        F --> G[Flag constraint_violations]
    end
    
    subgraph Act
        G --> H[Generate adjustments]
        H --> I[Create summary]
        I --> J[Set overall_score]
    end
    
    J --> K[Return to Client]
```

---

### 4. Agent Layer

#### VisionAnalyst

```mermaid
flowchart TB
    Input[Image Bytes] --> Preprocess[Image Preprocessing]
    Preprocess --> Gemini[Gemini 2.0 Flash Vision]
    Gemini --> Parse[JSON Parser]
    Parse --> Validate[Pydantic Validation]
    Validate --> Output[VisionOutput]
    
    subgraph Capabilities
        C1[Multi-food Detection]
        C2[Portion Estimation]
        C3[Bounding Box Extraction]
        C4[OCR for Text]
    end
```

**Gemini Integration:**
- Model: `gemini-2.0-flash`
- Features: Bounding box output, structured JSON response
- Retry policy: 3 attempts with exponential backoff

#### BioDataScout

```mermaid
flowchart TB
    Query[User ID] --> Fetch[Fetch Health Data]
    Fetch --> Mock[HealthKit Mock]
    Mock --> Process[Process Constraints]
    Process --> Output[BioDataReport]
    
    subgraph "Health Metrics"
        M1[Glucose Level]
        M2[Sleep Quality]
        M3[Activity Level]
        M4[Allergies]
    end
```

**Mock Data Schema:**
```python
{
    "glucose_mg_dl": 95,  # Normal: 70-100
    "sleep_quality": 0.7,  # 0-1 scale
    "activity_level": "moderate",
    "allergies": ["peanuts", "shellfish"],
    "dietary_restrictions": ["low_sodium"]
}
```

#### NutriAuditor

```mermaid
flowchart TB
    Foods[Detected Foods] --> Search[USDA Search]
    Search --> Match[Best Match Selection]
    Match --> Fetch[Fetch Nutrition Data]
    Fetch --> Calculate[Sum Nutrients]
    Calculate --> Compare[Compare to Targets]
    Compare --> Output[NutriAuditReport]
    
    Constraints[User Constraints] --> Compare
```

---

### 5. Tool Layer

#### USDA FoodData Central Integration

```mermaid
sequenceDiagram
    participant NA as NutriAuditor
    participant Cache as Local Cache
    participant API as USDA API
    
    NA->>Cache: Check cache(food_name)
    alt Cache hit
        Cache-->>NA: Return cached data
    else Cache miss
        NA->>API: GET /foods/search?query={food}
        API-->>NA: Search results
        NA->>API: GET /food/{fdc_id}
        API-->>NA: Nutrition data
        NA->>Cache: Store in cache
    end
```

**API Details:**
- Endpoint: `https://api.nal.usda.gov/fdc/v1`
- Auth: API key in header
- Rate limit: 1000 requests/hour

#### HealthKit Mock

For hackathon demo, simulates Apple HealthKit data:

| Metric | Type | Range | Update Frequency |
|--------|------|-------|------------------|
| Glucose | float | 70-180 mg/dL | Per request (randomized) |
| Sleep | float | 0-1 | Daily |
| Steps | int | 0-20000 | Hourly |
| Heart Rate | int | 50-120 bpm | Per request |

---

### 6. Evaluation Layer

#### Opik Observability

```mermaid
flowchart TB
    subgraph "Application Code"
        O[Orchestrator]
        A1[VisionAnalyst]
        A2[BioDataScout]
        A3[NutriAuditor]
    end
    
    subgraph "Opik SDK"
        Track["@track decorator"]
        Span[Custom Spans]
        Log[Metric Logging]
    end
    
    subgraph "Opik Dashboard"
        Traces[Trace Explorer]
        Metrics[Metrics View]
        Experiments[Experiments]
    end
    
    O --> Track
    A1 --> Track
    A2 --> Track
    A3 --> Track
    
    Track --> Traces
    Span --> Traces
    Log --> Metrics
    Metrics --> Experiments
```

**Tracked Events:**

| Event | Metadata |
|-------|----------|
| `orchestrator.process` | session_id, user_id, meal_type |
| `vision_analyst.analyze` | image_size, model, latency_ms |
| `biodata_scout.query` | user_id, constraints_count |
| `nutri_auditor.audit` | foods_count, violations_count |
| `usda_api.search` | query, results_count, cached |

#### Pycalib Confidence Calibration

```mermaid
flowchart LR
    Raw[Raw Confidence<br/>0.85] --> Platt[Platt Scaling]
    Platt --> Calibrated[Calibrated<br/>0.72]
    
    subgraph "Calibration Dataset"
        D1[Food Image 1]
        D2[Food Image 2]
        D3[Food Image N]
    end
    
    D1 & D2 & D3 --> Train[Train Calibrator]
    Train --> Platt
```

---

## Data Flow: End-to-End Request

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant API as FastAPI
    participant Orch as Orchestrator
    participant VA as VisionAnalyst
    participant Gemini as Gemini API
    participant BDS as BioDataScout
    participant NA as NutriAuditor
    participant USDA as USDA API
    participant Opik as Opik
    
    User->>FE: Upload food image
    FE->>API: POST /analyze (image, user_id)
    API->>Orch: process(input)
    Orch->>Opik: Start trace
    
    rect rgb(200, 220, 255)
        Note over Orch: OBSERVE Phase
        Orch->>VA: analyze(image)
        VA->>Gemini: Vision request
        Gemini-->>VA: Foods, portions, boxes
        VA-->>Orch: VisionOutput
    end
    
    rect rgb(200, 255, 220)
        Note over Orch: THINK Phase
        par Parallel queries
            Orch->>BDS: query(user_id)
            BDS-->>Orch: BioDataReport
        and
            Orch->>NA: audit(foods)
            NA->>USDA: Search + fetch
            USDA-->>NA: Nutrition data
            NA-->>Orch: NutriAuditReport
        end
    end
    
    rect rgb(255, 220, 200)
        Note over Orch: ACT Phase
        Orch->>Orch: Generate adjustments
        Orch->>Orch: Create summary
        Orch->>Orch: Score meal
    end
    
    Orch->>Opik: End trace
    Orch-->>API: MealState
    API-->>FE: JSON response
    FE-->>User: Display results
```

---

## Security Considerations

| Layer | Security Measure |
|-------|------------------|
| **API** | API key authentication, CORS whitelist |
| **Secrets** | Environment variables, never in code |
| **User Data** | No PII stored, session-based |
| **LLM** | Input sanitization, output validation |

---

## Deployment Architecture

```mermaid
flowchart TB
    subgraph "Vercel Edge"
        FE[Next.js App]
    end
    
    subgraph "Google Cloud"
        CR[Cloud Run<br/>FastAPI]
        SM[Secret Manager<br/>API Keys]
    end
    
    subgraph "External Services"
        Gemini[Gemini API]
        USDA[USDA API]
        Opik[Comet Opik]
    end
    
    FE --> CR
    CR --> SM
    CR --> Gemini
    CR --> USDA
    CR --> Opik
```

**Environment Variables:**
```bash
GEMINI_API_KEY=...
OPIK_API_KEY=...
USDA_API_KEY=...
OPIK_PROJECT_NAME=nutripilot
ENVIRONMENT=production
```

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| End-to-end latency | < 5s | API response time |
| Vision analysis | < 2s | VisionAnalyst duration |
| USDA lookup | < 500ms | Cached 95% of requests |
| Frontend load | < 2s | Lighthouse score > 90 |

---

## Future Extensions

1. **Real HealthKit Integration**: iOS app with native HealthKit access
2. **Meal Planning**: Proactive meal suggestions based on nutrient gaps
3. **Multi-language Support**: OCR and responses in multiple languages
4. **Continuous Learning**: Fine-tune portion estimation with user feedback
5. **Wearable Integration**: Real-time glucose monitoring (CGM)
