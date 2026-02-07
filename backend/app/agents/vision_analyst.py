"""
NutriPilot AI - VisionAnalyst Agent

Analyzes food images using Gemini 2.0 Flash Vision to detect:
- Food items with names and portions
- Portion sizes in grams with confidence scores
- Bounding box coordinates for each food item
- OCR text extraction for receipts/menus

This agent implements the OBSERVE phase of the pipeline.
"""

import asyncio
import base64
import json
import logging
import re
import time
from typing import Optional

# Try to import Opik for tracing
try:
    from opik import track
    OPIK_AVAILABLE = True
except ImportError:
    OPIK_AVAILABLE = False
    def track(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

import google.generativeai as genai

from app.core.base_agent import BaseAgent
from app.core.state import VisionInput, VisionOutput, FoodItem, BoundingBox
from app.config import get_settings

logger = logging.getLogger(__name__)


class VisionAnalyst(BaseAgent[VisionInput, VisionOutput]):
    """
    Specialized agent for food image analysis using Gemini Vision.
    
    Uses Gemini 2.0 Flash for:
    - Multi-food detection in single images
    - Portion size estimation based on visual cues
    - Bounding box extraction for food locations
    - OCR for text (menus, receipts, labels)
    
    Example:
        analyst = VisionAnalyst()
        result = await analyst.execute(VisionInput(
            image_bytes=image_data,
            image_format="jpeg"
        ))
    """
    
    def __init__(self, model_name: str = "gemini-2.0-flash", timeout_seconds: int = 30):
        """
        Initialize VisionAnalyst with Gemini model.
        
        Args:
            model_name: Gemini model to use (default: gemini-2.0-flash)
            timeout_seconds: Timeout for API calls (default: 30s)
        """
        super().__init__(max_retries=3, retry_delay=1.0)
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.settings = get_settings()
        
        # Configure Gemini API
        if self.settings.google_api_key:
            genai.configure(api_key=self.settings.google_api_key)
            self.model = genai.GenerativeModel(model_name)
        else:
            self.model = None
            logger.warning("Google API key not configured - VisionAnalyst will use mock data")
    
    @property
    def name(self) -> str:
        return "VisionAnalyst"
    
    @track(name="vision_analyst.process")
    async def process(self, input: VisionInput) -> VisionOutput:
        """
        Analyze a food image and detect all visible food items.
        
        Args:
            input: VisionInput with image bytes and format
            
        Returns:
            VisionOutput with detected foods, confidence, and optional OCR text
        """
        start_time = time.time()
        
        if not self.model:
            logger.warning("No Gemini model available, returning mock data")
            return self._get_mock_output()
        
        try:
            # Prepare image for Gemini
            image_base64 = base64.b64encode(input.image_bytes).decode("utf-8")
            
            # Create the analysis prompt
            prompt = self._build_analysis_prompt(input.context)
            
            # Call Gemini Vision API with timeout
            try:
                response = await asyncio.wait_for(
                    self.model.generate_content_async([
                        prompt,
                        {"mime_type": f"image/{input.image_format}", "data": image_base64}
                    ]),
                    timeout=self.timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"Gemini Vision API timed out after {self.timeout_seconds}s"
                )
                # Return failure output with clear indication
                return VisionOutput(
                    foods=[],
                    overall_confidence=0.0,
                    model_used=self.model_name,
                    latency_ms=self.timeout_seconds * 1000,
                )
            
            # Parse the response
            output = self._parse_response(response.text)
            
            # Calculate latency
            output.latency_ms = int((time.time() - start_time) * 1000)
            output.model_used = self.model_name
            
            logger.info(
                f"VisionAnalyst detected {len(output.foods)} foods "
                f"with {output.overall_confidence:.2f} confidence in {output.latency_ms}ms"
            )
            
            return output
            
        except Exception as e:
            logger.error(f"Gemini Vision analysis failed: {e}")
            # Return failure output instead of mock data for non-food images
            return VisionOutput(
                foods=[],
                overall_confidence=0.0,
                model_used=self.model_name,
            )
    
    def _build_analysis_prompt(self, context: Optional[str] = None) -> str:
        """Build the prompt for Gemini Vision analysis."""
        base_prompt = """You are an expert nutritionist AI analyzing a food image. Your task is to analyze food images with clinical precision.

Identify ALL visible food items with precise details. For each food:
1. **Name**: Be specific (e.g., "grilled chicken breast" not just "chicken")
2. **Portion**: Use pixel-pointing to estimate volume (ml) or weight (gm) based on visual cues (plate size, utensils, hands)
3. **Description**: Human-readable portion (e.g., "1 medium fillet", "2 cups")
4. **Confidence**: Your certainty in the identification (0.0 to 1.0)
5. **Bounding Box**: Normalized coordinates [x1, y1, x2, y2] where values are 0-1

Return your analysis as a valid JSON object with this EXACT structure:
```json
{
    "foods": [
        {
            "name": "grilled chicken breast",
            "portion_grams": 150,
            "portion_description": "1 medium breast",
            "confidence": 0.92,
            "bounding_box": {"x1": 0.1, "y1": 0.2, "x2": 0.4, "y2": 0.5}
        }
    ],
    "overall_confidence": 0.88,
    "ocr_text": null
}
```

Guidelines:
- Include ALL distinct food items visible
- Estimate portion sizes conservatively
- If text is visible (menu, receipt, label), include in ocr_text
- Set overall_confidence based on image quality and food visibility"""
        
        if context:
            base_prompt += f"\n\nAdditional context: {context}"
        
        return base_prompt
    
    def _parse_response(self, response_text: str) -> VisionOutput:
        """Parse Gemini's response into VisionOutput."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find raw JSON object
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    json_str = json_match.group()
                else:
                    raise ValueError("No JSON found in response")
            
            data = json.loads(json_str)
            
            # Parse foods
            foods = []
            for food_data in data.get("foods", []):
                # Parse bounding box if present
                bbox = None
                if "bounding_box" in food_data and food_data["bounding_box"]:
                    bbox_data = food_data["bounding_box"]
                    try:
                        bbox = BoundingBox(
                            x1=float(bbox_data.get("x1", 0)),
                            y1=float(bbox_data.get("y1", 0)),
                            x2=float(bbox_data.get("x2", 1)),
                            y2=float(bbox_data.get("y2", 1)),
                        )
                    except Exception:
                        bbox = None  # Skip invalid bounding boxes
                
                food = FoodItem(
                    name=food_data.get("name", "unknown food"),
                    portion_grams=float(food_data.get("portion_grams", 100)),
                    portion_description=food_data.get("portion_description", "1 serving"),
                    confidence=float(food_data.get("confidence", 0.5)),
                    bounding_box=bbox,
                )
                foods.append(food)
            
            return VisionOutput(
                foods=foods,
                ocr_text=data.get("ocr_text"),
                overall_confidence=float(data.get("overall_confidence", 0.7)),
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse Gemini response: {e}")
            # Return minimal output on parse failure
            return VisionOutput(
                foods=[],
                overall_confidence=0.0,
            )
    
    def _get_mock_output(self) -> VisionOutput:
        """Return mock output for testing without API."""
        return VisionOutput(
            foods=[
                FoodItem(
                    name="grilled chicken breast",
                    portion_grams=150,
                    portion_description="1 medium breast",
                    confidence=0.92,
                    bounding_box=BoundingBox(x1=0.1, y1=0.15, x2=0.45, y2=0.5),
                ),
                FoodItem(
                    name="steamed brown rice",
                    portion_grams=200,
                    portion_description="1 cup",
                    confidence=0.88,
                    bounding_box=BoundingBox(x1=0.5, y1=0.2, x2=0.85, y2=0.55),
                ),
                FoodItem(
                    name="steamed broccoli",
                    portion_grams=100,
                    portion_description="1 cup florets",
                    confidence=0.90,
                    bounding_box=BoundingBox(x1=0.2, y1=0.55, x2=0.5, y2=0.85),
                ),
            ],
            overall_confidence=0.87,
            model_used="mock",
            latency_ms=50,
        )
