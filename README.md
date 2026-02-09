# Artworks API

A simple REST API for browsing and filtering artwork listings, built with FastAPI.

## Setup

### 1. Create a virtual environment (recommended)

```bash
cd artworks-api
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the server

```bash
uvicorn main:app --reload
```

The API will be available at: `http://localhost:8000`

## Interactive Documentation

FastAPI automatically generates interactive docs:

- **Swagger UI**: http://localhost:8000/docs (recommended - you can test endpoints here!)
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### List all artworks
```
GET /artworks
```

### Filter artworks by type
```
GET /artworks?type=watercolor
GET /artworks?type=mixed-media
GET /artworks?type=large-canvas
GET /artworks?type=featured
```

### Filter by availability
```
GET /artworks?available=true
GET /artworks?available=false
```

### Filter by price range
```
GET /artworks?min_price=500
GET /artworks?max_price=1000
GET /artworks?min_price=500&max_price=1000
```

### Filter by year
```
GET /artworks?year=2024
```

### Combine multiple filters
```
GET /artworks?type=watercolor&available=true&min_price=300
```

### Get a single artwork
```
GET /artworks/1
```

### List all artwork types
```
GET /types
```

## Example Response

```json
{
  "total": 6,
  "filtered_count": 3,
  "artworks": [
    {
      "id": "1",
      "title": "Misty Sunlight",
      "description": "A celebration of what makes us uniquely human...",
      "types": ["watercolor", "featured"],
      "price": 450.0,
      "dimensions": "16x20 inches",
      "year": 2024,
      "available": true,
      "image_url": "https://..."
    }
  ]
}
```

## Adding New Artworks

Edit `data/artworks.json` to add, update, or remove artworks. The structure is:

```json
{
  "id": "unique-id",
  "title": "Artwork Title",
  "description": "Description of the artwork",
  "types": ["watercolor", "featured"],
  "price": 450.00,
  "dimensions": "16x20 inches",
  "year": 2024,
  "available": true,
  "image_url": "https://example.com/image.jpg"
}
```

## Project Structure

```
artworks-api/
├── main.py              # FastAPI application
├── data/
│   └── artworks.json    # Artwork data
├── requirements.txt     # Python dependencies
└── README.md           # This file
```
