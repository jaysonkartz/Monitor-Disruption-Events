# Mointor-Disruption-Events
 Fresh Code repo for mointoring Disruption events for Mirxes. Early warning and alert sys


# Demo Website
You can find the demo web application here:

https://artc-disruption-monitoring.streamlit.app/


# Installation

## 1. Create a virtual environment
```bash
py -m venv env ( python -m venv env ) For Microsoft installation 
```
## 2. Activate the virtual environment
```bash
env/Scripts/activate
```

## 3. pip Install the required packages
```bash
pip install -r requirements.txt
```

## 4. Secret Environment Variables

### 4.1 ``.env`` file
Create ```.env``` file in root directory using the ```.env.sample``` file as a template.

The supabase environment variables are fixed to my current supabase project. So you don't have to change them

You'll only have to change your ```OPENAI_API_KEY``` to your own key.

### 4.2 ``.streamlit`` directory

Create a `.streamlit` directory in the root directory. Then create a `secrets.toml` file in the `.streamlit` directory.

Copy contents from the `.env` file into the `secrets.toml` file.

#### Final Directory Structure

```
project-repo/
├── .streamlit/
│ ├── secrets.toml
├── .env.sample
├── .env
├── requirements.txt
├── README.md
├── archive/
│ ├── Experiments4.ipynb
│ ├── GoogleNewsWebscraping.ipynb
.
.
.
├── Todo.md
```


# Local Deployment
```bash
streamlit run App.py
```

# Directory Descriptions

- `App.py`: Main streamlit application file, contains all the web application code.
- `llm/`: All LLM code for data extraction of news articles for early warning. This is the main bulk of the important code
- `Supabase/`: Supabase utilities for Data insertion + Extraction to Cloud SQL Supabase
- `utils/`: Cointains 1. Webscraping code, 2. Supplier &Distruption Event Distance calculation 3. Risk Ranking calculation
- `NewsScrape/`: Deprecated code for webscraping news articles
- `src/`: Previously used for testing, never use already ( deprecated ) 
- `README.md`: This file you are currently reading.


