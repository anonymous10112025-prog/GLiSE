import json
from openai import OpenAI
from typing import List
from model.Settings import get_settings

QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "queries": {
            "type": "array",
            "description": "Raw generated search queries as strings, ready to use. Include nothing else but the raw queries.",
            "items": {
                "type": "string"
            }
        }
    },
    "required": ["queries"],
    "additionalProperties": False
}

class LLMProvider:
    def __init__(self, model: str, system_prompt: str = "", temperature: float = 0.2):
        """
        Initialize an LLM provider.

        Args:
            model: Name/identifier of the LLM model
            system_prompt: System prompt to set context for the LLM
            temperature: Sampling temperature for the LLM
        """
        self._model = model
        self._system_prompt = system_prompt
        self._temperature = temperature
        self._is_reasoning_model = self._check_if_reasoning_model(model)
    
    def call_llm(self, user_prompt: str) -> str:  
        settings = get_settings()
        api_key = settings.get('OPENAI_API_KEY')
        
        if not api_key:
            raise RuntimeError("OpenAI API key not configured. Please set it in Settings.")
        
        client = OpenAI(api_key=api_key)
        
        try:
            # Prepare common parameters
            params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
            }
            
            # Configure parameters based on model type
            if self._is_reasoning_model:
                # Reasoning models have specific requirements:
                # - Temperature must be 1.0 (only supported value)
                # - Do NOT include response_format (not supported)
                # - Need to explicitly request JSON in prompt instead
                params["temperature"] = 1.0
                # Add JSON format instruction to the user prompt for reasoning models
                enhanced_prompt = f"{user_prompt}\n\nIMPORTANT: Return your response as valid JSON following this exact schema: {json.dumps(QUERY_SCHEMA)}"
                params["messages"][1]["content"] = enhanced_prompt
            else:
                # Non-reasoning models: use user-specified temperature and JSON schema
                params["temperature"] = self.temperature
                params["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "query_schema",
                        "schema": QUERY_SCHEMA
                    }
                }
            
            resp = client.chat.completions.create(**params)

            return resp.choices[0].message.content.strip()

        except Exception as e:
            raise RuntimeError(f"LLM call failed: {e}")
    
    @staticmethod
    def _check_if_reasoning_model(model: str, llms_path: str = "data/data.json") -> bool:
        """
        Check if a model is a reasoning model based on data.json metadata.
        
        Args:
            model: Name of the model to check
            llms_path: Path to the data.json file
            
        Returns:
            True if model is a reasoning model, False otherwise (default)
        """
        try:
            with open(llms_path, "r") as f:
                data = json.load(f)
                for llm in data["llms"]:
                    if llm["model"] == model:
                        return llm.get("reasoning", False)
        except (FileNotFoundError, KeyError, json.JSONDecodeError):
            # If we can't read the file or find the model, assume non-reasoning (safer default)
            return False
        
        # Model not found in data.json - default to non-reasoning
        return False
    
    @staticmethod
    def get_model_choices(llms_path: str = "data/data.json") -> List[str]:
        """Retrieve available LLM model choices from data.json."""
        with open(llms_path, "r") as f:
            data = json.load(f)
            return [llm["model"] for llm in data["llms"]]
    
    # Properties
    @property
    def model(self) -> str:
        """Get the current LLM model name."""
        return self._model
    
    @model.setter
    def model(self, value: str) -> None:
        """Set the LLM model name."""
        self._model = value
        self._is_reasoning_model = self._check_if_reasoning_model(value)
    
    @property
    def is_reasoning_model(self) -> bool:
        """Check if the current model is a reasoning model."""
        return self._is_reasoning_model
    
    @property
    def system_prompt(self) -> str:
        """Get the current system prompt."""
        return self._system_prompt
    
    @system_prompt.setter
    def system_prompt(self, value: str) -> None:
        """Set the system prompt."""
        self._system_prompt = value
    
    @property
    def temperature(self) -> float:
        """Get the current temperature setting."""
        return self._temperature
    
    @temperature.setter
    def temperature(self, value: float) -> None:
        """
        Set the sampling temperature.
        
        Args:
            value: Sampling temperature (typically 0.0 to 2.0)
        
        Raises:
            ValueError: If temperature is negative
        """
        if value < 0:
            raise ValueError("Temperature must be non-negative")
        self._temperature = value
