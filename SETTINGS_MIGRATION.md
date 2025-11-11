# Settings & Configuration Guide

> 📚 **Quick Start:** See [QUICKSTART.md](QUICKSTART.md) for a beginner-friendly getting started guide.

## Overview
The application uses a JSON-based settings system with a user-friendly GUI for configuration management. All settings are stored in `settings.json` at the project root.

## How to Configure Settings

### Via GUI (Recommended)
1. Launch the application
2. Go to **File > Settings** (or press **Ctrl+,**)
3. Configure your settings in the three tabs:
   - **API Keys**: Enter your API keys (password-protected fields)
   - **Query Defaults**: Set default model, prompts, and query counts
   - **Search Settings**: Choose your search engine configuration
4. Click **Save**
5. Settings are saved to `settings.json` and persist across sessions

### Settings File Location
- Settings are stored in `settings.json` at the project root
- This file contains your API keys - **never commit it to Git**
- A template file `settings.json.template` shows the required structure

## Available Settings

### API Keys Tab
Configure your API credentials for various services:

| Setting | Description | Get Key Link | Required |
|---------|-------------|--------------|----------|
| **OPENAI_API_KEY** | OpenAI API for query generation & ML filtering | [Get Key](https://platform.openai.com/api-keys) | ✅ Yes |
| **GOOGLE_API_KEY** | Google API for web search | [Get Key](https://console.cloud.google.com/apis/credentials) | ✅ Yes |
| **GOOGLE_CSE_CX** | Google Custom Search Engine ID | [Get Key](https://programmablesearchengine.google.com/controlpanel/all) | ✅ Yes |
| **GITHUB_TOKEN** | GitHub personal access token (increases rate limits) | [Get Key](https://github.com/settings/tokens) | ⚠️ Optional |
| **STACKEXCHANGE_API_KEY** | Stack Exchange API key (increases quota) | [Get Key](https://stackapps.com/apps/oauth/register) | ⚠️ Optional |

### Query Defaults Tab
Set default values for query generation:

| Setting | Default | Description |
|---------|---------|-------------|
| **Model** | gpt-4o | AI model to use (gpt-4o, gpt-4o-mini, gpt-5, etc.) |
| **System Prompt** | Custom | Instructions for how the AI should behave |
| **Temperature** | 0.2 | Creativity level (0.0-2.0, lower = more focused) |
| **Total Queries** | 10 | Total number of queries to generate |
| **Google Gray Lit** | 5 | Number of Google gray literature queries |
| **Google Docs** | 5 | Number of Google documentation queries |

### Search Settings Tab
Configure search behavior:

| Setting | Default | Description |
|---------|---------|-------------|
| **Max Results/Query** | 50 | Maximum results per individual query |
| **Max Results/Provider** | 100 | Maximum total results per provider |
| **Sleep Between Calls** | 1.0 sec | Delay between API calls (prevents rate limiting) |
| **OpenAI Tier** | free | Your API usage tier (affects rate limits) |



## Features

### Date Range Filtering
Filter search results by publication date:
- **How to use**: Select From/To dates in the query generation form
- **Supported by**: All search providers (GitHub, Stack Overflow, Google)
- **Persistence**: Date ranges are saved with your query generations
- **Format**: Dates use YYYY-MM-DD format (e.g., 2024-01-01)

### Provider-Specific Filtering
- **GitHub**: Filters by repository/issue creation date
- **Stack Overflow**: Filters by question creation date  
- **Google**: Filters by page publication date (extracted from snippets)

## Troubleshooting

### Settings Not Saving
- Make sure you clicked the **Save** button in the Settings window
- Check that `settings.json` exists in the project root folder
- Verify you have write permissions in the project directory

### API Keys Not Working
- Verify your API keys are correct (copy/paste carefully)
- Check that you've enabled the required APIs in your provider accounts
- For GitHub: Ensure your token has appropriate permissions
- For Google: Make sure both API Key and CSE CX are configured

### Double Save Prompt
This issue has been fixed. If you still see it:
- Make sure you're running the latest version
- Try restarting the application

## Security Notes

⚠️ **Important**: 
- Never commit `settings.json` to Git - it contains your API keys
- The `.gitignore` file is configured to exclude it automatically
- If you accidentally commit it, immediately regenerate all your API keys
- Use `settings.json.template` to share configuration structure without secrets

## Related Documentation

- 📚 [QUICKSTART.md](QUICKSTART.md) - Getting started guide for new users
- 📖 [README.md](README.md) - Installation and setup instructions
