# Provider Architecture Refactoring

## Overview

The Grey Literature provider system has been refactored into a cleaner, object-oriented architecture using polymorphism and the Strategy pattern. Each search provider is now a separate class with its own `search()` method implementation.

## Architecture

### Base Class: `GLProvider` (Abstract)

Located in `model/providers/base_provider.py`

**Responsibilities:**
- Define the interface for all providers
- Implement common query generation logic
- Handle prompt template loading
- Provide utility methods for JSON parsing and language instructions

**Key Methods:**
- `search(query, max_results)` - Abstract method that each provider must implement
- `generate_queries(...)` - Generate search queries using LLM
- `get_id()`, `get_name()`, `get_prompt_template_path()` - Class methods for provider metadata

### Concrete Provider Classes

All located in `model/providers/`:

1. **GoogleProvider** (`google_provider.py`)
   - ID: `google`
   - Supports both SerpAPI and Google Custom Search Engine
   - Auto-selects backend based on `ENV_ENGINE` setting
   - Extracts metadata from page maps (metatags, schema descriptions)

2. **GitHubCodeProvider** (`github_code_provider.py`)
   - ID: `gh_code`
   - Searches GitHub code repositories
   - Requires `GITHUB_TOKEN` for API access
   - Returns code file results with repository information

3. **GitHubIssuesProvider** (`github_issues_provider.py`)
   - ID: `gh_issues`
   - Searches GitHub Issues and Pull Requests
   - Includes issue state, comments count
   - Full body text in snippets

4. **GitHubReposProvider** (`github_repos_provider.py`)
   - ID: `gh_repos`
   - Searches GitHub repositories
   - Fetches README contents using GraphQL batching
   - Includes star count, language, and full README

5. **StackOverflowProvider** (`stackoverflow_provider.py`)
   - ID: `so`
   - Searches Stack Overflow via Stack Exchange API
   - Includes answer status, score
   - Full question body in snippets

## Usage

### New Way (Recommended)

```python
from model.providers import get_provider, get_all_providers

# Get a specific provider
google = get_provider("google")
results = google.search("machine learning Python", max_results=10)

# Get all providers
all_providers = get_all_providers()
for provider_id, provider in all_providers.items():
    print(f"{provider.name}: {provider.id}")
```

### Old Way (Backward Compatible)

```python
from model.GLProvider import GLProvider

# Still works - uses backward compatibility wrapper
providers = GLProvider.get_providers_list()
provider = providers["google"]
results = provider.search("machine learning Python", max_results=10)
```

## Benefits

### 1. **Separation of Concerns**
- Each provider's search logic is isolated in its own file
- Easy to understand and maintain individual providers
- Changes to one provider don't affect others

### 2. **Polymorphism**
- All providers implement the same `search()` interface
- Can be used interchangeably
- Easy to iterate over all providers

### 3. **Testability**
- Each provider can be tested independently
- Mock providers can be created easily for testing
- No dependency on JSON configuration for core logic

### 4. **Extensibility**
- Adding a new provider is straightforward:
  1. Create new class extending `GLProvider`
  2. Implement required methods
  3. Add to `PROVIDER_CLASSES` in `__init__.py`
  4. No changes to existing code needed

### 5. **Type Safety**
- Clear interfaces defined by abstract base class
- Better IDE autocomplete and type checking
- Compile-time error detection

### 6. **Configuration via Code**
- Provider metadata (ID, name, prompts) defined in class methods
- Easier to refactor and search for usage
- No need to keep JSON in sync with code

## Migration Guide

### For Existing Code

No changes required! The old `GLProvider` class still works as a backward compatibility wrapper.

### For New Code

Use the new provider architecture:

```python
# Old way
from model.GLProvider import GLProvider
providers = GLProvider.get_providers_list()
google = providers["google"]

# New way  
from model.providers import get_provider
google = get_provider("google")
```

### Adding a New Provider

1. Create a new file in `model/providers/`:

```python
# model/providers/my_new_provider.py
from model.providers.base_provider import GLProvider
from model.Settings import get_settings

class MyNewProvider(GLProvider):
    @classmethod
    def get_id(cls) -> str:
        return "my_provider"
    
    @classmethod
    def get_name(cls) -> str:
        return "My New Search Provider"
    
    @classmethod
    def get_prompt_template_path(cls) -> str:
        return "data/GLProvidersPrompts/MyPrompt.txt"
    
    def search(self, query: str, max_results: int = 50):
        # Implement search logic
        results = []
        # ... your search API calls here ...
        return results
```

2. Register in `model/providers/__init__.py`:

```python
from model.providers.my_new_provider import MyNewProvider

PROVIDER_CLASSES = {
    # ... existing providers ...
    "my_provider": MyNewProvider,
}
```

3. Create prompt template in `data/GLProvidersPrompts/MyPrompt.txt`

4. Done! Your provider is now available via `get_provider("my_provider")`

## File Structure

```
model/
├── GLProvider.py              # Backward compatibility wrapper
├── providers/
│   ├── __init__.py           # Factory functions and exports
│   ├── base_provider.py      # Abstract base class
│   ├── google_provider.py    # Google search implementation
│   ├── github_code_provider.py
│   ├── github_issues_provider.py
│   ├── github_repos_provider.py
│   └── stackoverflow_provider.py
```

## Removed Dependencies

- ~~`data/data.json` providers section~~ - Provider configuration now in code
- ~~Large monolithic search functions~~ - Moved into provider classes
- ~~Global API key variables~~ - Now loaded via Settings per provider

## Key Design Patterns

1. **Abstract Factory** - `get_provider()` creates provider instances
2. **Strategy** - Different search strategies encapsulated in provider classes
3. **Template Method** - `generate_queries()` in base class, `search()` in subclasses
4. **Singleton-like** - `get_settings()` for configuration access

## Testing

Each provider can be tested independently:

```python
# Test Google provider
google = GoogleProvider()
results = google.search("test query", max_results=5)
assert len(results) <= 5
assert all('url' in r for r in results)

# Test with mock settings
from unittest.mock import patch
with patch('model.providers.google_provider.get_settings') as mock_settings:
    mock_settings.return_value.get.return_value = "test_api_key"
    results = google.search("test")
```

## Performance Considerations

- **Lazy loading**: Providers are only instantiated when requested
- **Efficient deduplication**: URL-based dedup to avoid duplicate results
- **Rate limiting**: Built-in sleep delays between API requests
- **GraphQL batching**: GitHub Repos provider batches README fetches

## Future Enhancements

1. **Caching**: Add result caching layer to avoid redundant API calls
2. **Async/Parallel**: Make searches async for faster execution
3. **Retry Logic**: Add automatic retry with exponential backoff
4. **Rate Limit Handling**: Detect and handle rate limit responses
5. **Result Ranking**: Add scoring/ranking algorithm for results
6. **Plugin System**: Dynamic provider loading from external modules
