# Unstructured Document Data Extraction

A web application for extracting structured data from PDF documents using predefined schemas.

## Features

- Upload PDF documents and extract data based on predefined schemas
- View extracted data in a clean user interface
- Download annotated PDFs showing identified data fields
- Support for multiple document types including receipts, invoices, and utility bills

## Tech Stack

- **Backend**: Python/Flask
- **Frontend**: React/Next.js
- **Data Processing**: Custom PDF extraction pipeline
- **Storage**: File-based storage for documents and results

## Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- npm or pnpm

## Installation

### Backend Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd unstructured-demo
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install the required Node.js packages:
   ```bash
   npm install
   # Or if using pnpm
   pnpm install
   ```

## Running the Application

### Start the Backend Server

1. From the root directory with your virtual environment activated:
   ```bash
   python app.py
   ```
   The backend server will start at http://localhost:5000

### Start the Frontend Development Server

1. In a new terminal, navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Start the development server:
   ```bash
   npm run dev
   # Or if using pnpm
   pnpm run dev
   ```
   The frontend will be available at http://localhost:3000

## Testing the Application

1. Open your browser and navigate to http://localhost:3000
2. Select a document schema from the dropdown menu
3. Upload a PDF document to extract data

### Test with Sample Data

To test the application with the provided sample electricity bill:

1. Select the 'electricity bill' schema from the dropdown
2. Upload the file `input/I-575655elec_flat.pdf`
3. View the extracted data and annotated PDF

## Available Schemas

The application comes with three predefined schemas:

- **Electricity Bill**: For extracting data from utility bills
- **Invoice**: For extracting data from business invoices
- **Receipt**: For extracting data from general receipts

## Project Structure

```
unstructured-demo/
├── annotated_pdfs/     # Storage for annotated PDFs
├── api_responses/      # API response samples
├── app.py             # Flask application entry point
├── extract.py         # PDF extraction logic
├── frontend/          # React/Next.js frontend
├── input/             # Sample input documents
├── requirements.txt   # Python dependencies
├── results/           # Extraction results storage
└── schemas/           # Document schemas
    ├── electricity_bill.json
    ├── invoice.json
    └── receipt.json
```

