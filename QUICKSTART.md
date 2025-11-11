<p align="center">
  <img src="icon.png" alt="GLiSE Logo" width="128" height="128">
</p>

# Quick Start Guide - GLiSE

> 📚 **This guide is for end users.** For technical installation details, see [README.md](README.md).
> 
> 🔧 **For settings architecture details**, see [SETTINGS_MIGRATION.md](SETTINGS_MIGRATION.md).

## First Time Setup

### 1. Install the Application

**Create and activate a conda environment:**
```powershell
conda create -n wx_env python=3.8
conda activate wx_env
```

**Install GLiSE in editable mode:**
```powershell
pip install -e .
```

This installs all dependencies automatically from `pyproject.toml`.

### 2. Get Your API Keys

#### Required:
- **OpenAI API Key**: https://platform.openai.com/api-keys
  - Sign up/login to OpenAI
  - Click "Create new secret key"
  - Copy the key (starts with `sk-`)
  - **Used for**: Query generation & ML filtering (text embeddings)

- **Google Custom Search API Key**: https://console.cloud.google.com/apis/credentials
  - Create a new project or use existing
  - Enable "Custom Search API"
  - Create credentials → API Key
  - Copy the API key

- **Google Custom Search Engine ID**: https://programmablesearchengine.google.com/controlpanel/all
  - Create a new search engine
  - Set it to "Search the entire web"
  - Copy the Search Engine ID (CX)

#### Optional:
- **GitHub Token**: https://github.com/settings/tokens
  - For searching GitHub repositories and issues
  - Increases rate limits
  
- **Stack Exchange API Key**: https://stackapps.com/apps/oauth/register
  - For searching Stack Overflow and related sites
  - Increases request quota

### 3. Configure the Application

#### Method 1: Using the GUI (Recommended)
1. Run the application:
   ```powershell
   python view/generate_queries_form_window.py
   ```
2. Go to **File > Settings** (or press `Ctrl+,`)
3. In the **API Keys** tab:
   - Paste your **OpenAI API Key**
   - Paste your **Google API Key**
   - Paste your **Google CSE Engine ID (CX)**
   - (Optional) Add GitHub Token and Stack Exchange API Key
4. In the **Query Defaults** tab:
   - Select your preferred **LLM Model** (gpt-4o, gpt-4o-mini, etc.)
   - Adjust **Temperature** for query creativity
   - Set default number of queries to generate
5. In the **OpenAI Settings** tab:
   - Select your **OpenAI Tier** (affects rate limiting for embeddings)
6. Click **Save**

#### Method 2: Manual Configuration
1. Copy the template file:
   ```powershell
   Copy-Item settings.json.template settings.json
   ```
2. Edit `settings.json` with your favorite text editor
3. Replace the empty strings with your API keys:
   ```json
   {
     "OPENAI_API_KEY": "sk-your-key-here",
     "GOOGLE_API_KEY": "your-google-api-key",
     "GOOGLE_CSE_CX": "your-search-engine-id",
     "OPENAI_TIER": "free",
     ...
   }
   ```

### 4. Test Your Setup

Run the test script:
```powershell
python test_settings.py
```

You should see:
```
✓ Settings system working correctly!
```

### 5. Start Using the Tool

1. **Launch the application:**
   
   **Option A - Using the command (if wx_env is activated):**
   ```powershell
   conda activate wx_env
   glise
   ```
   
   **Option B - Using Python directly:**
   ```powershell
   python app.py
   ```

2. Fill in the **Query Generation** form:
   - **LLM Model**: Choose your preferred GPT model (gpt-4o, gpt-4o-mini, gpt-5, etc.)
   - **Temperature**: Adjust creativity (0.0 = focused, 2.0 = creative)
   - **System Prompt**: Customize the LLM's behavior
   - **Description**: Describe what you're searching for
   - **Sources**: Check the providers you want to use:
     - Google (general web search)
     - GitHub Repositories
     - GitHub Issues
     - Stack Exchange
   - **Parameters**: Set number of queries to generate
   - **Languages**: Enter programming languages (if applicable)

3. Click **Generate Queries** to create search queries

4. In the **Results Window**:
   - Review generated queries organized by provider
   - Adjust **Max Results** settings if needed
   - Click **Search** to execute queries
   - Click **Save to Storage** to save queries for later

5. In the **Search Results Window**:
   - View all search results organized by provider
   - Apply **ML Filtering**:
     - Select "No filter" to see all results
     - Select "text-embedding-3-small" for faster, lightweight filtering
     - Select "text-embedding-3-large" for more accurate filtering
     - Click **Apply Filter** to filter results
   - Review filtered results and relevance scores
   - Click **Save Results** to persist filtered results to storage

## Common Issues

### "OpenAI API key not configured"
- Open Settings (File > Settings)
- Make sure your OpenAI API key is entered in the API Keys tab
- Click Save

### "No settings found, creating default settings.json"
- This is normal on first run
- The application creates the file automatically
- Configure your API keys in Settings (File > Settings)

### "LLM call failed: Error code: 401"
- Your OpenAI API key is invalid or expired
- Get a new key from https://platform.openai.com/api-keys
- Update it in Settings

### "Google search failed" or "No results from Google"
- Check your Google API Key is valid
- Check your Google CSE Engine ID (CX) is correct
- Verify Custom Search API is enabled in Google Cloud Console
- Check you haven't exceeded your daily quota (100 free searches/day)

### Queries not being generated
1. Check that at least one provider is selected
2. Verify Description field is not empty
3. Check that System Prompt is not empty
4. Look at the console for error messages
5. Verify OpenAI API key is configured

### ML Filtering not working
1. Check OpenAI API key is configured (needed for embeddings)
2. Verify ML model files exist in `models-ml/` directory
3. Check your OpenAI tier setting matches your actual tier
4. Look for rate limit errors in console output

## Tips

1. **Start Small**: Generate 5-10 queries first to test
2. **Adjust Temperature**: 
   - Use 0.0-0.3 for very specific, technical queries
   - Use 0.5-0.8 for balanced results (recommended)
   - Use 0.9-2.0 for creative, diverse queries
3. **Customize System Prompt**: Add specific instructions like:
   - "Focus on recent developments"
   - "Include both beginner and advanced queries"
   - "Emphasize practical implementation examples"
4. **ML Filtering Strategy**:
   - Use **text-embedding-3-small** for faster filtering (good for large result sets)
   - Use **text-embedding-3-large** for better accuracy (slower, more API tokens)
   - Filtered results are cached - you can switch between filters without re-filtering
5. **Manage API Quotas**:
   - Set **Max Results Per Query** lower (e.g., 20-30) to reduce API calls
   - Configure your **OpenAI Tier** correctly for proper rate limiting
   - GitHub search benefits from a personal access token (higher rate limits)
6. **Save Your Work**: 
   - Use "Save to Storage" to persist query generations
   - Use "Save Results" to persist search results with filters
   - All saves are stored in `storage/[instance_id]/` folder

## Need Help?

- 📚 **Installation issues?** Check [README.md](README.md) for technical troubleshooting
- 🔧 **Settings system details?** See [SETTINGS_MIGRATION.md](SETTINGS_MIGRATION.md)
- 💬 **Error messages?** Check the console output for detailed error information
- 🔑 **API key problems?** Make sure all API keys are valid and have sufficient quota
- 🐛 **Found a bug?** Check existing issues or create a new one on GitHub

## File Structure

```
GLTool_workspace/
├── pyproject.toml          # Package configuration
├── app.py                  # Application entry point
├── icon.png                # Application icon
├── settings.json           # Your configuration (DO NOT commit to Git)
├── settings.json.template  # Template showing structure
├── storage/                # Saved query generations and search results
│   └── [timestamp_id]/
│       ├── info.json           # Generation metadata
│       ├── queries.json        # Generated queries
│       ├── results.json        # Search results (no filter)
│       ├── results-small.json  # Filtered results (embedding-3-small)
│       └── results-large.json  # Filtered results (embedding-3-large)
├── models-ml/              # Pre-trained ML models for filtering
│   ├── GaussianNB-differences-large.joblib
│   ├── GaussianNB-differences-small.joblib
│   ├── Ridge-differences-large.joblib
│   ├── Ridge-differences-small.joblib
│   ├── XGBoost-differences-large.joblib
│   └── XGBoost-differences-small.joblib
├── data/
│   ├── GLProviders.json    # Search provider configurations
│   └── GLProvidersPrompts/ # Provider-specific prompt templates
├── model/                  # Data models (Settings, GLProvider, LLMProvider)
│   ├── Settings.py         # Settings management
│   ├── filtering/          # Strategy Pattern for ML filtering
│   └── providers/          # Search provider implementations
├── view/                   # GUI windows and dialogs
│   ├── settings_window.py  # Settings configuration UI
│   ├── icon_helper.py      # Centralized icon management
│   └── progress_windows/   # Progress dialogs
└── controller/             # Business logic
```
