"use client"

import { useState, useEffect } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { getAnnotatedPdfUrl } from "@/lib/api"
import dynamic from 'next/dynamic'

// Dynamically import react-pdf to avoid SSR issues with canvas
const PDFViewer = dynamic(
  () => import('react-pdf').then(mod => {
    const { Document, Page, pdfjs } = mod;
    // Initialize react-pdf
    pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;
    
    // Create a component that uses Document and Page
    return function PDFViewerComponent({ pdfFilename, extractedFields }: PDFViewerProps) {
      const [isClient, setIsClient] = useState(false)
      const [numPages, setNumPages] = useState<number>(0)
      const [pageNumber, setPageNumber] = useState<number>(1)
      const [pageWidth, setPageWidth] = useState<number>(600)
      const [pdfUrl, setPdfUrl] = useState<string>('')
    
      useEffect(() => {
        setIsClient(true)
        // Set the PDF URL
        if (pdfFilename) {
          setPdfUrl(getAnnotatedPdfUrl(pdfFilename))
        }
    
        // Set page width based on container size
        const updatePageWidth = () => {
          const container = document.querySelector('.pdf-container')
          if (container) {
            setPageWidth(container.clientWidth - 40) // 40px for padding
          }
        }
    
        updatePageWidth()
        window.addEventListener('resize', updatePageWidth)
        
        return () => {
          window.removeEventListener('resize', updatePageWidth)
        }
      }, [pdfFilename])
    
      const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
        setNumPages(numPages)
      }
    
      const goToNextPage = () => {
        if (pageNumber < numPages) {
          setPageNumber(pageNumber + 1)
        }
      }
    
      const goToPrevPage = () => {
        if (pageNumber > 1) {
          setPageNumber(pageNumber - 1)
        }
      }
    
      if (!isClient) {
        return <div className="h-full flex items-center justify-center">Loading PDF viewer...</div>
      }
    
      return (
        <div className="h-full flex flex-col">
          <div className="flex-1 bg-white dark:bg-gray-900 p-4 flex flex-col items-center justify-center relative pdf-container">
            {pdfUrl ? (
              <Document
                file={pdfUrl}
                onLoadSuccess={onDocumentLoadSuccess}
                loading={
                  <div className="h-[600px] w-full flex items-center justify-center">
                    <div className="text-center">
                      <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4"></div>
                      <p className="text-sm text-muted-foreground">Loading PDF...</p>
                    </div>
                  </div>
                }
                error={
                  <div className="h-[600px] w-full flex items-center justify-center">
                    <div className="text-center text-red-500">
                      <p>Failed to load PDF. Please try again.</p>
                    </div>
                  </div>
                }
              >
                <Page 
                  pageNumber={pageNumber} 
                  width={pageWidth}
                  renderTextLayer={false}
                  renderAnnotationLayer={false}
                />
              </Document>
            ) : (
              <div className="h-[600px] w-full flex items-center justify-center">
                <div className="text-center text-muted-foreground">
                  <p>No PDF available</p>
                </div>
              </div>
            )}
    
            {/* Pagination controls */}
            {numPages > 0 && (
              <div className="absolute bottom-4 left-0 right-0 flex items-center justify-center gap-2">
                <div className="bg-black/70 backdrop-blur-sm rounded-full flex items-center p-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    className={cn(
                      "h-8 w-8 rounded-full text-white hover:bg-white/20",
                      pageNumber <= 1 && "opacity-50 cursor-not-allowed",
                    )}
                    onClick={goToPrevPage}
                    disabled={pageNumber <= 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    <span className="sr-only">Previous page</span>
                  </Button>
    
                  <div className="px-3 text-xs text-white font-medium">
                    {pageNumber} / {numPages}
                  </div>
    
                  <Button
                    variant="ghost"
                    size="icon"
                    className={cn(
                      "h-8 w-8 rounded-full text-white hover:bg-white/20",
                      pageNumber >= numPages && "opacity-50 cursor-not-allowed",
                    )}
                    onClick={goToNextPage}
                    disabled={pageNumber >= numPages}
                  >
                    <ChevronRight className="h-4 w-4" />
                    <span className="sr-only">Next page</span>
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      );
    };
  }),
  { ssr: false }
);

interface PDFViewerProps {
  pdfFilename: string;
  extractedFields?: Record<string, any>;
}

export default function PDFViewerWrapper(props: PDFViewerProps) {
  return <PDFViewer {...props} />;
}

