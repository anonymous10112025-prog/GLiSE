# Settings System - Technical Documentation

> 📚 **For end users:** See [QUICKSTART.md](QUICKSTART.md) for a beginner-friendly settings guide.
> 
> 🔧 **For developers:** This document provides technical details about the settings architecture.

## Overview
Successfully replaced `.env` file dependency with a JSON-based settings system that provides a user-friendly GUI for configuration management.

This document serves as both:
- **Migration guide**: How we moved from `.env` to `settings.json`
- **Architecture documentation**: How the Settings system works internally

## Files Created

### 1. `model/Settings.py` (NEW)
- **Purpose**: Core settings management class with JSON persistence
- **Key Features**:
  - `DEFAULTS` dictionary with all default configuration values
  - `API_KEY_URLS` mapping to provider registration pages
  - `load()` and `save()` methods for JSON persistence
  - `get_settings()` singleton pattern
  - Settings stored in `settings.json` at project root

### 2. `view/settings_window.py` (NEW)
- **Purpose**: GUI window for editing application settings
- **Features**:
  - Three-tab interface:
    - **API Keys Tab**: Password-style fields with show/hide toggles, "Get Key" buttons linking to provider sites
    - **Query Defaults Tab**: Model selection, system prompt, temperature, query numbers
    - **Search Settings Tab**: ENV_ENGINE choice (serpapi/google_cse)
  - Save/Reset/Close buttons
  - Unsaved changes detection with confirmation dialog
  - Direct integration with Settings model

### 3. `settings.json.template` (NEW)
- **Purpose**: Template file showing required settings structure
- **Usage**: Safe to commit to Git (no secrets), shows users what they need to configure

### 4. `test_settings.py` (NEW)
- **Purpose**: Test script to verify Settings system functionality
- **Usage**: Run to ensure settings.json creation and persistence works

## Files Modified

### 1. `view/generate_queries_form_window.py`
**Changes**:
- Added `from model.Settings import get_settings`
- Added `from view.settings_window import SettingsWindow`
- Added `self.settings = get_settings()` in `__init__`
- Added menu bar with File > Settings (Ctrl+,) and Help > About
- Added `on_open_settings()` method to launch SettingsWindow
- **Migrated all `os.getenv()` calls to `self.settings.get()`**:
  - `QUERY_DEFAULT_MODEL` for LLM model selection
  - `QUERY_FORGE_TEMPERATURE` for temperature spinner
  - `QUERY_FORGE_ROLE` for system prompt text
  - `QUERIES_DEFAULT_NUMBER` for queries number spinner
  - `QUERIES_DEFAULT_GOOGLE_GRAY_NUMBER` for Google gray literature spinner
  - `QUERIES_DEFAULT_GOOGLE_DOC_NUMBER` for Google documentation spinner

### 2. `model/LLMProvider.py`
**Changes**:
- Replaced `from dotenv import load_dotenv` with `from model.Settings import get_settings`
- Updated `call_llm()` method:
  - Now gets API key from Settings: `settings.get('OPENAI_API_KEY')`
  - Explicitly passes API key to `OpenAI(api_key=api_key)`
  - Added validation: raises error if API key not configured

### 3. `.gitignore`
**Changes**:
- Added `settings.json` to prevent committing API keys to Git
- `settings.json.template` is tracked to show users the structure

### 4. `README.md`
**Changes**:
- Updated installation instructions (step 4)
- Removed reference to `.env` file
- Added comprehensive Settings documentation:
  - How to configure via GUI (File > Settings)
  - Required API keys with links to get them
  - Description of all configurable settings
  - Warning about not committing settings.json

## Settings Configuration

### API Keys
- **OPENAI_API_KEY**: https://platform.openai.com/api-keys (Required for query generation & ML filtering)
- **GOOGLE_API_KEY**: https://console.cloud.google.com/apis/credentials (Required for search)
- **GOOGLE_CSE_CX**: https://programmablesearchengine.google.com/controlpanel/all (Required search engine ID)
- **GITHUB_TOKEN**: https://github.com/settings/tokens (Optional, increases rate limits)
- **STACKEXCHANGE_API_KEY**: https://stackapps.com/apps/oauth/register (Optional, increases quota)

### Query Defaults
- **QUERY_DEFAULT_MODEL**: "gpt-4o" (available: gpt-4o, gpt-4o-mini, gpt-4o-realtime, gpt-5, gpt-5-nano)
- **QUERY_FORGE_ROLE**: System prompt for LLM behavior
- **QUERY_FORGE_TEMPERATURE**: 0.2 (0.0-2.0, lower = more focused)
- **QUERIES_DEFAULT_NUMBER**: 10 (total queries to generate)
- **QUERIES_DEFAULT_GOOGLE_GRAY_NUMBER**: 5 (Google gray literature queries)
- **QUERIES_DEFAULT_GOOGLE_DOC_NUMBER**: 5 (Google documentation queries)

### Search & Performance Settings
- **MAX_RESULTS_PER_QUERY_DEFAULT**: 50 (maximum results per individual query)
- **MAX_RESULTS_PER_PROVIDER_DEFAULT**: 100 (maximum total results per provider)
- **SLEEP_BETWEEN**: 1.0 (seconds to wait between API calls)

### OpenAI Tier Settings
- **OPENAI_TIER**: Your API usage tier affects rate limits for embeddings
  - Options: "free", "tier_1", "tier_2", "tier_3", "tier_4", "tier_5"
  - Free tier: 280k TPM, 500 RPM
  - Tier 5: 80M TPM, 10k RPM
- **EMBEDDING_OVERHEAD_PER_INPUT**: 150 (token overhead per embedding request)

### OpenAI Settings
- **OPENAI_TIER**: Your API usage tier affects rate limits for embeddings ("free", "tier_1", "tier_2", "tier_3", "tier_4", "tier_5")

## Migration Status

### ✅ Fully Migrated
- `view/generate_queries_form_window.py`: All 6 `os.getenv()` calls → `self.settings.get()`
- `model/LLMProvider.py`: OpenAI API key now from Settings
- Settings GUI fully functional with Save/Load

### 📝 Notes
- `controller/queries_generate_split.py`: Contains `os.getenv()` calls in `main()` function, but these are only used for CLI execution, not GUI
- The GUI passes all parameters explicitly to `generate_queries()`, so no migration needed
- `load_dotenv()` kept in main window for backward compatibility with existing `.env` files

## Testing

### Quick Test
Run the test script to verify Settings system:
```powershell
python test_settings.py
```

### Manual Testing
1. Launch the application
2. Go to File > Settings (or Ctrl+,)
3. Configure your API keys in the API Keys tab
4. Adjust defaults in Query Defaults tab
5. Choose search engine in Search Settings tab
6. Click Save
7. Close and reopen the application
8. Verify settings were persisted

## Benefits of New Settings System

1. **User-Friendly**: GUI for non-technical users, no need to edit text files
2. **Secure**: Password-style fields for API keys
3. **Convenient**: "Get Key" buttons link directly to provider registration pages
4. **Persistent**: JSON format is easy to read and edit if needed
5. **Git-Safe**: settings.json excluded from version control
6. **Discoverable**: Menu item (File > Settings) makes configuration obvious
7. **Validated**: Checks for required settings before use
8. **Cross-Platform**: JSON works on all operating systems

## Package Configuration

After removing `setup.py` and `requirements.txt`, the project now uses modern Python packaging:

### Current: `pyproject.toml` (Single Source of Truth)
```toml
[project]
name = "GLiSE"
version = "1.0.0"
dependencies = [
    "wxPython",
    "python-dotenv",
    "openai",
    "requests",
    "tiktoken",
    "joblib",
    "bs4",
    "xgboost",
    "scikit-learn"
]

[project.scripts]
glise = "app:main"

[tool.setuptools]
py-modules = ["app"]
packages = ["model", "view", "controller", "data"]
```

**Benefits:**
- Modern Python packaging standard (PEP 518, 621)
- No more duplicate configuration files
- Automatic dependency installation with `pip install -e .`
- Console script `glise` automatically registered
- Package data (icons, prompts, models) automatically included

## Next Steps (Optional Enhancements)

1. ✅ **Completed**: Removed duplicate config files (`setup.py`, `requirements.txt`)
2. Add settings validation in SettingsWindow (e.g., check API key format)
3. Add "Test Connection" buttons for each API key
4. Add settings export/import functionality
5. Add encrypted storage for API keys (using keyring library)
6. Add settings backup before overwriting
7. Add settings migration from .env to settings.json on first run

## Backward Compatibility

- `load_dotenv()` still called in main window for users with existing `.env` files
- Settings system takes precedence over environment variables
- Users can gradually migrate from `.env` to `settings.json`

## Related Documentation

- 📚 [QUICKSTART.md](QUICKSTART.md) - End user guide for getting started
- 📖 [README.md](README.md) - Technical installation and setup guide
- 🏗️ This document - Architecture and implementation details
