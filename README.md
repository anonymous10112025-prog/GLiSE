<p align="center">
  <img src="icon.png" alt="GLiSE Logo" width="128" height="128">
</p>

# GLiSE - Grey Literature Search Engine

[![arXiv](https://img.shields.io/badge/arXiv-2512.23066-b31b1b.svg)](https://arxiv.org/abs/2512.23066)
[![MSR 2026](https://img.shields.io/badge/MSR-2026-blue.svg)](https://conf.researchr.org/home/msr-2026)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.18806216-blue.svg)](https://doi.org/10.5281/zenodo.18806216)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> ⭐ **If you use GLiSE in your research, please star the repository and cite our MSR 2026 paper.**
>
> 📚 **New to this tool?** Start with [QUICKSTART.md](QUICKSTART.md) for a beginner-friendly guide.
> 
> 🔧 **For developers:** This README covers technical installation and setup.

A tool for collecting grey literature from various sources for software engineering research.

## 📄 Research Paper

This tool has been accepted at the **23rd International Mining Software Repositories Conference (MSR 2026)** — Data and Tool Showcase Track (co-located with ICSE 2026).

📌 **Preprint:** [arXiv:2512.23066](https://arxiv.org/abs/2512.23066)  
🔗 **Source Code:** [GitHub Repository](https://github.com/anonymous10112025-prog/GLiSE)  
📦 **DOI:** [10.5281/zenodo.18806216](https://doi.org/10.5281/zenodo.18806216)

## 📚 Citation

If you use this tool in your research, please cite our paper:

```bibtex
@misc{GLiSE_2026,
      title={GLiSE: A Prompt-Driven and ML-Powered Tool for Automated Grey Literature Extraction in Software Engineering}, 
      author={Houcine Abdelkader Cherief and Brahim Mahmoudi and Zacharie Chenail-Larcher and Naouel Moha and Quentin Stiévenart and Florent Avellaneda},
      year={2026},
      eprint={2512.23066},
      archivePrefix={arXiv},
      primaryClass={cs.SE},
      url={https://arxiv.org/abs/2512.23066},
      doi= {10.5281/zenodo.18806216},
      note={The first three authors contributed equally to this work and share first authorship}
}
```

> 📌 **Note:** This paper has been accepted at MSR 2026 (Tool Track). The official ACM citation will replace this preprint citation once published.

## Project Structure

```
GLTool_workspace/
├── pyproject.toml          # Package configuration (single source of truth)
├── settings.json           # Your configuration (DO NOT commit to Git)
├── settings.json.template  # Template showing structure
├── app.py                  # Application entry point
├── icon.png                # Application icon
├── storage/                # Saved query generations and search results
├── models-ml/              # Pre-trained ML models for filtering
├── data/
│   ├── GLProviders.json    # Search provider configurations
│   └── GLProvidersPrompts/ # Provider-specific prompt templates
├── model/                  # Data models (Settings, GLProvider, LLMProvider)
├── view/                   # GUI windows and dialogs
└── controller/             # Business logic
```

## Model training and datasets

This repository also includes assets used for training and evaluating machine learning models related to result relevance-based filtering:

- `model_search_and_train_script/` — contains the scripts used to train and evaluate the filtering models (for example, provider-specific training pipelines such as `github_repository_models_training.py`, `stackoverflow_models_training.py`, and a combined `all_models_train_and_test.py`). Use these scripts to reproduce training runs, adjust model hyperparameters, or run evaluation suites.

- `datasets - filtrated datasets/` — contains the filtrated datasets used for training and evaluation. These are processed/filtered datasets derived from collected search results and are used as inputs to the training pipelines and for offline evaluation. Treat these files as datasets for experimentation; check the individual JSON/CSV files for column schemas and provenance information.

- `GLiSE Usability Study.xlsx` — spreadsheet with the results from the GLiSE usability study. The file is included in the repository root (or data folder).

### Install Steps

These instructions show how to install the project in editable/development mode using pip.

Prerequisites

- Python 3.8+ (use the version required by the project in `pyproject.toml`).
- It's recommended to use a virtual environment (venv or conda).
- **Important**: Install the exact package versions specified in `pyproject.toml` to ensure ML model compatibility and consistent filtering results. Using different versions of scikit-learn or xgboost may cause the pre-trained models to produce different or incorrect predictions.


Install steps (editable mode)

1. **Create and activate a virtual environment** (conda is recommended):

	```powershell
	conda create -n wx_env python=3.8
	conda activate wx_env
	```

2. **Install the package in editable mode** from the project root:

	```powershell
	pip install -e .
	```

	This will automatically install all dependencies from `pyproject.toml`.

3. **Configure Settings** - On first run, the application will create a `settings.json` file. You can configure your API keys and preferences through the Settings window (File > Settings) in the application GUI, or manually edit the `settings.json` file.

   > 📖 See [QUICKSTART.md](QUICKSTART.md) for detailed API key setup instructions.
   > 
   > 🔧 See [SETTINGS_MIGRATION.md](SETTINGS_MIGRATION.md) for technical details about the settings system.

   **Important**: Never commit `settings.json` to Git as it contains your API keys. A template file `settings.json.template` is provided to show the required configuration structure.

   **Required API Keys**:
   - **OPENAI_API_KEY**: Required for LLM-based query generation and ML filtering
     - Get it from: https://platform.openai.com/api-keys
   - **GOOGLE_API_KEY**: Required for Google Custom Search
     - Get it from: https://console.cloud.google.com/apis/credentials
   - **GOOGLE_CSE_CX**: Google Custom Search Engine ID
     - Get it from: https://programmablesearchengine.google.com/controlpanel/all
   
   **Optional API Keys**:
   - **GITHUB_TOKEN**: For GitHub search features
   - **STACKEXCHANGE_API_KEY**: For Stack Exchange search

   **Key Settings**:
   - **QUERY_DEFAULT_MODEL**: Default LLM model (e.g., "gpt-4o", "gpt-4o-mini", "gpt-5")
   - **QUERY_FORGE_ROLE**: System prompt for the LLM
   - **QUERY_FORGE_TEMPERATURE**: LLM temperature (0.0-2.0)
   - **QUERIES_DEFAULT_NUMBER**: Default number of queries to generate
   - **MAX_RESULTS_PER_QUERY_DEFAULT**: Maximum search results per query (default: 50)
   - **MAX_RESULTS_PER_PROVIDER_DEFAULT**: Maximum results per provider (default: 100)
   - **OPENAI_TIER**: Your OpenAI API tier ("free", "tier_1" through "tier_5") for rate limiting

Editable installs let you change the source code in this repository and immediately use those changes without reinstalling.

## Running the Application

After installation, you can run GLiSE in several ways:

### Option 1: Command Line (if wx_env is activated)
```powershell
conda activate wx_env
glise
```

### Option 2: Python Module
```powershell
python app.py
```

### Option 3: Direct Python Import
```powershell
python -c "from app import main; main()"
```

## Usage

See [QUICKSTART.md](QUICKSTART.md) for a complete usage tutorial including:
- How to generate queries
- How to search grey literature sources
- How to apply ML filtering
- Common issues and solutions
- Tips for best results

## Troubleshooting

### "ModuleNotFoundError: No module named 'app'"
- Make sure you're in the `wx_env` conda environment
- Run `pip install -e .` again to reinstall the package

### "Command 'glise' not found"
- Make sure your conda environment is activated: `conda activate wx_env`
- Or run directly: `python app.py`

### "OpenAI API key not configured"
- Open Settings (File > Settings) in the application
- Enter your OpenAI API key in the API Keys tab
- Click Save

### Import errors or missing dependencies
- Reinstall in editable mode: `pip install -e .`
- All dependencies are specified in `pyproject.toml`

For more troubleshooting, see [QUICKSTART.md](QUICKSTART.md)

