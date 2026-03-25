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
pip install -r ../requirements.txt
```

2. Configure API endpoint (optional):
```bash
# Copy the example secrets file
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# Edit secrets.toml with your API URL
```

3. Run the application:
```bash
streamlit run app.py
```

## Usage

1. **Upload Image**: Select an image file (JPG, JPEG, PNG, GIF, BMP)
2. **Add Recommendations**: Click "+ Add Recommendation" and fill in:
   - Title: Brief description of the recommendation
   - Type: Select from Contrast & Salience, Composition, Colour & Mood, or Copy & Messaging
   - Description: Detailed description of the desired edit
3. **Configure Brand Guidelines** (optional):
   - Protected Regions: List areas that should not be modified
   - Typography Guidelines: Rules for text elements
   - Aspect Ratio: Required output ratio (e.g., 16:9)
   - Brand Elements: Guidelines for brand visibility
4. **Submit**: Click "Submit Job" to start processing
5. **Monitor**: Track job progress and view results when complete

## API Endpoints Used

- `POST /process` - Submit image for processing
- `GET /status/{job_id}` - Check job status
- `GET /result/{job_id}` - Retrieve completed job results
