# AI Image Processing Frontend

A Streamlit-based frontend for the AI Image Processing Application.

## Features

- Upload images for processing
- Add visual recommendations (title, description, type)
- Configure brand guidelines (protected regions, typography, aspect ratio, brand elements)
- Track job status in real-time
- View generated variants with evaluation scores

## Setup

1. Install dependencies:
```bash
cd frontend
pip install -r requirements.txt
```

2. Configure API endpoint (optional):
```bash
# Copy the example secrets file
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

3. Edit secrets.toml with the backend API URL

4. Run the application:
```bash
streamlit run app.py
```

## Usage

Access the frontend from http://localhost:8501/.
