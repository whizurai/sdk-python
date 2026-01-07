"""
AI Labs Image Service Client
Python SDK for image generation, enhancement, and analysis
"""
import httpx
from typing import Optional, List, Dict, Any, Literal
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ImageData:
    """Generated image data"""
    url: str
    revised_prompt: Optional[str] = None
    b64_json: Optional[str] = None


@dataclass
class ImageGenerateResponse:
    """Response from image generation"""
    images: List[ImageData]
    model: str
    cost_cents: int
    created_at: datetime
    cache_hit: bool


@dataclass
class PromptEnhanceResponse:
    """Response from prompt enhancement"""
    enhanced_prompt: str
    original_prompt: str
    cost_cents: int
    created_at: datetime


@dataclass
class ImageAnalyzeResponse:
    """Response from image analysis"""
    description: str
    details: Dict[str, Any]
    cost_cents: int
    created_at: datetime


class ImageClient:
    """
    Client for AI Labs Image Service
    
    Provides methods for:
    - Image generation from prompts
    - Prompt enhancement
    - Image alteration
    - Image analysis
    
    Example:
        >>> client = ImageClient(api_url="https://api.ai-labs.com", api_key="sk-...")
        >>> response = await client.generate("A serene mountain landscape")
        >>> print(response.images[0].url)
    """
    
    def __init__(
        self,
        api_url: str,
        api_key: Optional[str] = None,
        timeout: int = 120
    ):
        """
        Initialize image client
        
        Args:
            api_url: Base URL for AI Labs API (e.g., https://api.ai-labs.com)
            api_key: API key for authentication (optional)
            timeout: Request timeout in seconds (default: 120)
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        
        # Create httpx client
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        self.client = httpx.AsyncClient(
            base_url=self.api_url,
            headers=headers,
            timeout=timeout
        )
    
    async def generate(
        self,
        prompt: str,
        model: Literal["dall-e-2", "dall-e-3"] = "dall-e-3",
        size: str = "1024x1024",
        quality: Literal["standard", "hd"] = "standard",
        style: Literal["vivid", "natural"] = "vivid",
        n: int = 1,
        user_id: Optional[str] = None
    ) -> ImageGenerateResponse:
        """
        Generate images from a text prompt
        
        Args:
            prompt: Text description of the image to generate
            model: Model to use (dall-e-2 or dall-e-3)
            size: Image size (e.g., 1024x1024, 1024x1792, 1792x1024)
            quality: Image quality (standard or hd) - DALL-E 3 only
            style: Image style (vivid or natural) - DALL-E 3 only
            n: Number of images to generate (1-10)
            user_id: Optional user ID for tracking
        
        Returns:
            ImageGenerateResponse with generated images and metadata
        
        Raises:
            httpx.HTTPStatusError: If the API request fails
        
        Example:
            >>> response = await client.generate(
            ...     "A beautiful sunset over mountains",
            ...     model="dall-e-3",
            ...     size="1024x1024"
            ... )
            >>> print(f"Generated {len(response.images)} images")
        """
        payload = {
            "prompt": prompt,
            "model": model,
            "size": size,
            "quality": quality,
            "style": style,
            "n": n
        }
        
        if user_id:
            payload["user_id"] = user_id
        
        response = await self.client.post("/v1/image/generate", json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        return ImageGenerateResponse(
            images=[ImageData(**img) for img in data["images"]],
            model=data["model"],
            cost_cents=data["cost_cents"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            cache_hit=data.get("cache_hit", False)
        )
    
    async def enhance_prompt(
        self,
        simple_prompt: str,
        style_preferences: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> PromptEnhanceResponse:
        """
        Enhance a simple prompt to a detailed one using GPT-4
        
        Args:
            simple_prompt: Simple text description
            style_preferences: Optional style preferences (e.g., 'professional', 'artistic')
            user_id: Optional user ID for tracking
        
        Returns:
            PromptEnhanceResponse with enhanced prompt
        
        Example:
            >>> response = await client.enhance_prompt(
            ...     "sunset at beach",
            ...     style_preferences="professional photography"
            ... )
            >>> print(response.enhanced_prompt)
        """
        payload = {"simple_prompt": simple_prompt}
        
        if style_preferences:
            payload["style_preferences"] = style_preferences
        if user_id:
            payload["user_id"] = user_id
        
        response = await self.client.post("/v1/image/enhance-prompt", json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        return PromptEnhanceResponse(
            enhanced_prompt=data["enhanced_prompt"],
            original_prompt=data["original_prompt"],
            cost_cents=data["cost_cents"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        )
    
    async def alter(
        self,
        image_url: str,
        instructions: str,
        model: Literal["dall-e-2", "dall-e-3"] = "dall-e-3",
        user_id: Optional[str] = None
    ) -> ImageGenerateResponse:
        """
        Alter an existing image based on instructions
        
        Uses Vision API to analyze the image, then generates a new image
        incorporating the requested changes.
        
        Args:
            image_url: URL of the image to alter
            instructions: Description of changes to make
            model: Model to use (dall-e-2 or dall-e-3)
            user_id: Optional user ID for tracking
        
        Returns:
            ImageGenerateResponse with altered image
        
        Example:
            >>> response = await client.alter(
            ...     "https://example.com/original.png",
            ...     "Make it more colorful and add dramatic lighting"
            ... )
            >>> print(response.images[0].url)
        """
        payload = {
            "image_url": image_url,
            "instructions": instructions,
            "model": model
        }
        
        if user_id:
            payload["user_id"] = user_id
        
        response = await self.client.post("/v1/image/alter", json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        return ImageGenerateResponse(
            images=[ImageData(**img) for img in data["images"]],
            model=data["model"],
            cost_cents=data["cost_cents"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            cache_hit=data.get("cache_hit", False)
        )
    
    async def analyze(
        self,
        image_url: str,
        detail: Literal["low", "high", "auto"] = "auto",
        user_id: Optional[str] = None
    ) -> ImageAnalyzeResponse:
        """
        Analyze an image using GPT-4 Vision
        
        Args:
            image_url: URL of the image to analyze
            detail: Analysis detail level (low, high, auto)
            user_id: Optional user ID for tracking
        
        Returns:
            ImageAnalyzeResponse with analysis results
        
        Example:
            >>> response = await client.analyze(
            ...     "https://example.com/image.png",
            ...     detail="high"
            ... )
            >>> print(response.description)
        """
        payload = {
            "image_url": image_url,
            "detail": detail
        }
        
        if user_id:
            payload["user_id"] = user_id
        
        response = await self.client.post("/v1/image/analyze", json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        return ImageAnalyzeResponse(
            description=data["description"],
            details=data["details"],
            cost_cents=data["cost_cents"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check service health
        
        Returns:
            Health status dictionary
        """
        response = await self.client.get("/health")
        response.raise_for_status()
        return response.json()
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get service metrics
        
        Returns:
            Metrics dictionary
        """
        response = await self.client.get("/v1/metrics")
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# Convenience function
def create_image_client(
    api_url: str,
    api_key: Optional[str] = None,
    timeout: int = 120
) -> ImageClient:
    """
    Create an image client instance
    
    Args:
        api_url: Base URL for AI Labs API
        api_key: API key for authentication (optional)
        timeout: Request timeout in seconds
    
    Returns:
        ImageClient instance
    """
    return ImageClient(api_url=api_url, api_key=api_key, timeout=timeout)

