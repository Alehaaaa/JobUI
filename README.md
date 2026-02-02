# JobUI

JobUI is a job application tracker and manager designed to help VFX artists find and organize job openings from various studios.

## Core Component (PySide)

The core application is built using **Python** and **PySide6** and is primarily designed to run as a tool within **Autodesk Maya**, though the core logic can be adapted for standalone use.

The main codebase is located in the root directory.

### Features
- **Studio Scrapers**: Configurable scrapers for major VFX studios (Disney, ILM, DNEG, etc.).
- **Job Management**: View, filter, and track job listings.
- **Maya Integration**: Dockable UI within Maya.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/Alehaaaa/JobUI.git
    cd JobUI
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### In Maya
Add the repository root to your `PYTHONPATH`.

Run the tool in Maya's python script editor:

```python
import JobUI
JobUI.show()
```

### Standalone (Testing)
You can run the test scraper script to verify studio configurations:

```bash
python test_scraper.py [studio_id]
```

## Mac Native Version

The native macOS application (built with Swift/Xcode) is maintained on a separate branch.

> **Note**: To access the Mac native version, switch to the `mac` branch:
>
> ```bash
> git checkout mac
> ```

## Project Structure

- `main.py`: Main entry point.
- `ui/`: User Interface components.
- `core/`: Scraper logic and configuration managers.
- `config/`: Studio configuration JSONs.
- `utils/`: Utility functions.
- `requirements.txt`: Python dependencies.
