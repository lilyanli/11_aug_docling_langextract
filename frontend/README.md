# Document Processing UI - Frontend

A modern Next.js web application for uploading and processing financial documents with AI-powered extraction.

## Features

- **Drag & Drop Upload**: Easy file upload with drag and drop interface
- **Real-time Progress**: Live progress tracking during document processing
- **Results Preview**: Interactive preview of extracted data
- **Multiple Export Formats**: Download results as CSV, JSON, and PDF
- **Processing History**: View and manage previous document processing jobs
- **Responsive Design**: Works on desktop and mobile devices

## Tech Stack

- **Next.js 15** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Radix UI** - Accessible components
- **React Hook Form** - Form handling
- **React Dropzone** - File upload
- **Lucide React** - Icons

## Getting Started

### Prerequisites

- Node.js 18+ 
- pnpm (recommended) or npm

### Installation

1. **Install dependencies**:
   ```bash
   pnpm install
   # or
   npm install
   ```

2. **Start development server**:
   ```bash
   pnpm dev
   # or
   npm run dev
   ```

3. **Open your browser**:
   Navigate to [http://localhost:3000](http://localhost:3000)

## Project Structure

```
frontend/
├── app/                    # Next.js app directory
│   ├── api/               # API routes
│   │   ├── upload/        # File upload endpoint
│   │   ├── status/        # Job status endpoint
│   │   ├── result/        # Results endpoint
│   │   ├── history/       # History endpoint
│   │   └── download/      # File download endpoint
│   ├── globals.css        # Global styles
│   ├── layout.tsx         # Root layout
│   └── page.tsx           # Home page
├── components/            # React components
│   ├── ui/               # Reusable UI components
│   └── upload-page.tsx   # Main upload interface
├── hooks/                # Custom React hooks
├── lib/                  # Utility functions
├── public/               # Static assets
└── styles/               # Additional styles
```

## API Integration

The frontend is designed to work with a backend API that provides:

### Endpoints

- `POST /api/upload` - Upload document file
- `GET /api/status/[job_id]` - Get processing status
- `GET /api/result/[hash]` - Get processing results
- `GET /api/history` - Get processing history
- `GET /api/download/[hash]/[filename]` - Download result files

### Expected Backend Response Format

```typescript
type StatusResponse = {
  job_id: string
  state: "queued" | "processing" | "extracting" | "done" | "error"
  progress: number
  message?: string
  entities?: Record<string, any> | null
  downloads?: Record<string, string> | null
  preview?: any | null
  doc_type?: "fund_financials" | "investor_report" | "generic"
  hash?: string
}
```

## Current Implementation

The application has been cleaned of all mock data and is ready for backend integration. The API routes are set up with placeholder functions that will connect to the Python backend:

1. **API routes are ready** - All endpoints are configured for backend integration
2. **File upload interface** - Ready to send files to Python backend
3. **Status polling** - Ready to check real backend status
4. **Result display** - Ready to show actual backend results

## Backend Integration Status

✅ **Mock data removed** - All fake data has been cleaned up  
✅ **API structure ready** - Routes are prepared for backend calls  
⏳ **Backend connection** - Ready to connect to Python backend API  
⏳ **Real data flow** - Ready to process actual documents

## Development

### Available Scripts

- `pnpm dev` - Start development server
- `pnpm build` - Build for production
- `pnpm start` - Start production server
- `pnpm lint` - Run ESLint

### Environment Variables

Create a `.env.local` file for environment variables:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Deployment

The application can be deployed to Vercel, Netlify, or any other Next.js-compatible platform.

### Vercel Deployment

1. Push code to GitHub
2. Connect repository to Vercel
3. Deploy automatically

## Integration with Python Backend

To connect this frontend with the Python backend:

1. **Update API routes** to call Python backend endpoints
2. **Configure CORS** on Python backend
3. **Set up file upload** to Python backend
4. **Map response formats** between frontend and backend

See the backend documentation for API integration details.
