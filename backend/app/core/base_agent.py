"""
NutriPilot AI - Base Agent Abstract Class

Defines the common interface and utilities for all specialized agents.
All agents inherit from BaseAgent and implement the process() method.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any
from pydantic import BaseModel

# Try to import Opik for tracing
try:
    from opik import track
    OPIK_AVAILABLE = True
except ImportError:
    OPIK_AVAILABLE = False
    # Create a no-op decorator if Opik is not available
    def track(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

logger = logging.getLogger(__name__)

# Type variables for input/output types
InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class AgentError(Exception):
    """Base exception for agent errors."""
    
    def __init__(self, agent_name: str, message: str, original_error: Exception | None = None):
        self.agent_name = agent_name
        self.message = message
        self.original_error = original_error
        super().__init__(f"[{agent_name}] {message}")


class AgentResult(BaseModel):
    """Wrapper for agent execution results with metadata."""
    success: bool
    output: Any
    error: str | None = None
    latency_ms: int = 0
    agent_name: str = ""


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """
    Abstract base class for all NutriPilot agents.
    
    All agents follow the same pattern:
    1. Receive typed input (Pydantic model)
    2. Process the input (may call external APIs)
    3. Return typed output (Pydantic model)
    
    Features:
    - Automatic Opik tracing with @track decorator
    - Structured logging
    - Error handling and retries
    - Latency tracking
    
    Usage:
        class MyAgent(BaseAgent[MyInput, MyOutput]):
            @property
            def name(self) -> str:
                return "MyAgent"
            
            async def process(self, input: MyInput) -> MyOutput:
                # Your logic here
                return MyOutput(...)
    """
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize the agent.
        
        Args:
            max_retries: Maximum number of retry attempts for transient failures
            retry_delay: Base delay between retries (exponential backoff applied)
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._logger = logging.getLogger(f"nutripilot.agent.{self.name}")
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the agent's name for logging and tracing."""
        pass
    
    @abstractmethod
    async def process(self, input: InputT) -> OutputT:
        """
        Process the input and return output.
        
        This is the main method that subclasses must implement.
        
        Args:
            input: Typed input data
            
        Returns:
            Typed output data
            
        Raises:
            AgentError: If processing fails after all retries
        """
        pass
    
    async def execute(self, input: InputT) -> AgentResult:
        """
        Execute the agent with error handling and tracing.
        
        This method wraps process() with:
        - Latency tracking
        - Error handling
        - Logging
        
        Use this method instead of calling process() directly.
        
        Args:
            input: Typed input data
            
        Returns:
            AgentResult with success status, output, and metadata
        """
        start_time = time.time()
        
        self._logger.info(f"Starting {self.name} execution")
        
        try:
            output = await self.process(input)
            latency_ms = int((time.time() - start_time) * 1000)
            
            self._logger.info(f"{self.name} completed in {latency_ms}ms")
            
            return AgentResult(
                success=True,
                output=output,
                latency_ms=latency_ms,
                agent_name=self.name,
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            
            self._logger.error(f"{self.name} failed after {latency_ms}ms: {error_msg}")
            
            return AgentResult(
                success=False,
                output=None,
                error=error_msg,
                latency_ms=latency_ms,
                agent_name=self.name,
            )
    
    async def execute_with_retry(self, input: InputT) -> AgentResult:
        """
        Execute with automatic retries on transient failures.
        
        Uses exponential backoff between retries.
        
        Args:
            input: Typed input data
            
        Returns:
            AgentResult from the first successful attempt or last failed attempt
        """
        import asyncio
        
        last_result = None
        
        for attempt in range(self.max_retries):
            result = await self.execute(input)
            
            if result.success:
                return result
            
            last_result = result
            
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2 ** attempt)
                self._logger.warning(
                    f"{self.name} attempt {attempt + 1} failed, "
                    f"retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
        
        return last_result or AgentResult(
            success=False,
            output=None,
            error="Max retries exceeded",
            agent_name=self.name,
        )
    
    def _log_input(self, input: InputT, truncate: int = 200):
        """Log input data for debugging (truncated for large inputs)."""
        input_str = str(input.model_dump())
        if len(input_str) > truncate:
            input_str = input_str[:truncate] + "..."
        self._logger.debug(f"Input: {input_str}")
    
    def _log_output(self, output: OutputT, truncate: int = 200):
        """Log output data for debugging (truncated for large outputs)."""
        output_str = str(output.model_dump())
        if len(output_str) > truncate:
            output_str = output_str[:truncate] + "..."
        self._logger.debug(f"Output: {output_str}")
