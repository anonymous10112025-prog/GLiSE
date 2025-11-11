import json
import os
from typing import Dict, Any, Optional


class Settings:
    """Manages application settings with JSON persistence."""
    
    # Default settings
    DEFAULTS = {
        # API Keys
        "OPENAI_API_KEY": "",
        "GOOGLE_API_KEY": "",
        "GOOGLE_CSE_CX": "",
        "STACKEXCHANGE_API_KEY": "",
        "GITHUB_TOKEN": "",
        
        # Query Generation Defaults
        "QUERIES_DEFAULT_NUMBER": 10,
        "QUERY_DEFAULT_MODEL": "gpt-4o",
        "QUERY_FORGE_ROLE": "You are a senior query designer for developer OSINT. Return ONLY compact, high-signal search queries. No commentary.",
        "QUERY_FORGE_TEMPERATURE": 0.2,
        
        # Search Settings
        "MAX_RESULTS_PER_QUERY_DEFAULT": 50,
        "MAX_RESULTS_PER_PROVIDER_DEFAULT": 100,
        "SLEEP_BETWEEN": 1.0,
        
        # OpenAI Embeddings Settings
        "OPENAI_TIER": "free",  # Default to Free Tier
        "EMBEDDING_OVERHEAD_PER_INPUT": 150  # Tokens overhead per input for embeddings
    }
    
    # API Key URLs for help buttons
    API_KEY_URLS = {
        "OPENAI_API_KEY": "https://platform.openai.com/api-keys",
        "GOOGLE_API_KEY": "https://console.cloud.google.com/apis/credentials",
        "GOOGLE_CSE_CX": "https://programmablesearchengine.google.com/controlpanel/all",
        "STACKEXCHANGE_API_KEY": "https://stackapps.com/apps/oauth/register",
        "GITHUB_TOKEN": "https://github.com/settings/tokens"
    }
    
    def __init__(self, settings_file: str = "settings.json"):
        """
        Initialize settings manager.
        
        Args:
            settings_file: Path to settings file (relative to project root)
        """
        self.settings_file = settings_file
        self._settings: Dict[str, Any] = {}
        self.load()
    
    def get_settings_path(self) -> str:
        """Get absolute path to settings file."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(project_root, self.settings_file)
    
    def load(self):
        """Load settings from JSON file, create with defaults if doesn't exist."""
        settings_path = self.get_settings_path()
        
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    self._settings = json.load(f)
                # Merge with defaults to add any new settings
                for key, value in self.DEFAULTS.items():
                    if key not in self._settings:
                        self._settings[key] = value
            except Exception as e:
                # Silent fail, use defaults
                self._settings = self.DEFAULTS.copy()
        else:
            # Use defaults and save
            self._settings = self.DEFAULTS.copy()
            self.save()
    
    def save(self):
        """Save current settings to JSON file."""
        settings_path = self.get_settings_path()
        try:
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            # Silent fail
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value.
        
        Args:
            key: Setting key
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        return self._settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """
        Set a setting value.
        
        Args:
            key: Setting key
            value: New value
        """
        self._settings[key] = value
    
    def get_all(self) -> Dict[str, Any]:
        """Get all settings as a dictionary."""
        return self._settings.copy()
    
    def update(self, settings: Dict[str, Any]):
        """
        Update multiple settings at once.
        
        Args:
            settings: Dictionary of settings to update
        """
        self._settings.update(settings)
    
    @staticmethod
    def get_api_key_url(key_name: str) -> Optional[str]:
        """
        Get the URL to obtain an API key.
        
        Args:
            key_name: Name of the API key setting
            
        Returns:
            URL string or None if not found
        """
        return Settings.API_KEY_URLS.get(key_name)


# Global settings instance
_settings_instance = None

def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
