# PDF Outline Extractor

Fast, accurate PDF outline extraction tool that identifies document titles and headings (H1, H2, H3) with page numbers.

## Quick Start

1. **Create directories and add your PDFs:**
   ```bash
   # Create input and output directories
   mkdir -p input output
   
   # Place your PDF files in the input directory
   ```

2. **Build and run:**
   ```bash
   # Build the Docker image
   docker build --platform linux/amd64 -t 1a .
   
   # Run the container
   docker run --rm -v $(pwd)/input:/app/input:ro -v $(pwd)/output:/app/output --network none 1a
   ```

3. **Get results:** Check the `output` directory for JSON files with extracted outlines.

## Docker Usage

```bash
# Build the image
docker build --platform linux/amd64 -t 1a .

# Run the extractor
docker run --rm -v $(pwd)/input:/app/input:ro -v $(pwd)/output:/app/output --network none 1a
``` 

## Output Format

```json
{
    "title": "Document Title",
    "outline": [
        {
            "level": "H1",
            "text": "Main Heading",
            "page": 0
        }
    ]
}
```

## Model and Approach

This solution uses a lightweight, rule-based approach for PDF outline extraction without heavy machine learning dependencies. The model analyzes text formatting properties (font size, boldness, positioning) and applies intelligent pattern matching to identify document structure.

Key components:
- **Title Detection**: Analyzes first page formatting to identify document titles using scoring based on font size, boldness, and position
- **Heading Classification**: Uses font size thresholds and formatting cues to classify headings into H1, H2, H3 levels
- **Document Type Recognition**: Applies specialized rules for different document types (technical docs, RFPs, forms)
- **Pattern Filtering**: Removes noise like page numbers, URLs, and form fields using regex patterns

## Requirements Compliance

- **Processing Speed**: Under 10 seconds for 50-page PDFs through efficient text parsing
- **Model Size**: Under 200MB footprint with no heavy ML dependencies 
- **Offline Operation**: Fully functional without internet connectivity
- **Architecture**: AMD64 platform compatible
