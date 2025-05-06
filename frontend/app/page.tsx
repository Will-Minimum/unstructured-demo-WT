"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import {
  Upload,
  FileText,
  CheckCircle,
  ChevronRight,
  AlertTriangle,
  FileSpreadsheet,
} from "lucide-react"
import { cn } from "@/lib/utils"
import PDFViewer from "@/components/pdf-viewer"
import LoadingSpinner from "@/components/loading-spinner"
import ExtractedDataTable from "@/components/extracted-data-table"
import Navbar from "@/components/navbar"
import { fetchSchemas, uploadFile, Schema, ExtractionResult } from "@/lib/api"

export default function Home() {
  const [step, setStep] = useState<"upload" | "processing" | "results">("upload")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedSchema, setSelectedSchema] = useState<string | null>(null)
  const [hoveredSchema, setHoveredSchema] = useState<string | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [schemas, setSchemas] = useState<Schema[]>([])
  const [error, setError] = useState<string | null>(null)
  const [extractionResult, setExtractionResult] = useState<ExtractionResult | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    // Fetch schemas when component mounts
    const loadSchemas = async () => {
      try {
        const data = await fetchSchemas()
        setSchemas(data)
      } catch (err) {
        setError("Failed to load schemas. Please refresh the page and try again.")
        console.error(err)
      }
    }
    
    loadSchemas()
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null)
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      // Check file type
      if (file.type !== 'application/pdf') {
        setError("Please select a PDF file")
        return
      }
      // Check file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        setError("File size exceeds 10MB limit")
        return
      }
      setSelectedFile(file)
    }
  }

  const handleSchemaSelect = (value: string) => {
    setSelectedSchema(value)
    setError(null)
  }

  const handleSchemaHover = (schemaId: string | null) => {
    setHoveredSchema(schemaId)
  }

  const handleSubmit = async () => {
    if (selectedFile && selectedSchema) {
      setError(null)
      setStep("processing")
      setIsProcessing(true)

      try {
        const result = await uploadFile(selectedFile, selectedSchema)
        setExtractionResult(result)
        setStep("results")
      } catch (err) {
        setStep("upload")
        setError(err instanceof Error ? err.message : "An error occurred during processing")
        console.error(err)
      } finally {
        setIsProcessing(false)
      }
    } else {
      if (!selectedFile) {
        setError("Please select a file")
      } else if (!selectedSchema) {
        setError("Please select a schema")
      }
    }
  }

  const handleReset = () => {
    setStep("upload")
    setSelectedFile(null)
    setSelectedSchema(null)
    setHoveredSchema(null)
    setIsProcessing(false)
    setExtractionResult(null)
    setError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const getActiveSchema = () => {
    return schemas.find((schema) => schema.id === (hoveredSchema || selectedSchema))
  }

  if (!mounted) return null

  return (
    <main className="flex min-h-screen flex-col particles-bg">
      <Navbar />

      <div className="container mx-auto p-4 py-8 mt-16">
        <div className="flex flex-col md:flex-row gap-6 min-h-[80vh]">
          {/* First Column - Upload & Schema Selection */}
          <div
            className={cn(
              "transition-all duration-500 ease-in-out rounded-xl overflow-hidden glass-card",
              step === "upload" ? "md:w-2/3" : "md:w-1/6",
            )}
          >
            {step === "upload" ? (
              <div className="h-full flex flex-col p-6">
                <div className="mb-6">
                  <h2 className="text-xl font-bold mb-1 flex items-center gap-2">Document Analysis</h2>
                  <p className="text-sm text-muted-foreground">Upload your document and select an extraction schema</p>
                </div>

                {error && (
                  <div className="mb-4 p-3 bg-red-500/10 text-red-600 dark:text-red-400 rounded-lg flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" />
                    <p className="text-sm">{error}</p>
                  </div>
                )}

                <div className="mb-8">
                  <div
                    className="border-2 border-dashed border-primary/20 rounded-xl p-8 text-center cursor-pointer hover:border-primary/50 transition-colors relative overflow-hidden group"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <div className="absolute inset-0 bg-primary/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleFileChange}
                      accept=".pdf"
                      className="hidden"
                    />
                    <div className="relative z-10">
                      <div className="bg-primary/10 p-4 rounded-full inline-block mb-4">
                        <Upload className="h-8 w-8 text-primary" />
                      </div>
                      <p className="text-sm font-medium mb-1">Click to upload or drag and drop</p>
                      <p className="text-xs text-muted-foreground mb-4">PDF (max 10MB)</p>

                      {selectedFile && (
                        <div className="mt-4 p-3 bg-primary/10 rounded-lg flex items-center gap-3 max-w-md mx-auto">
                          <div className="bg-primary/20 p-2 rounded-md">
                            <FileText className="h-5 w-5 text-primary" />
                          </div>
                          <div className="text-left flex-1 truncate">
                            <p className="text-sm font-medium truncate">{selectedFile.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                            </p>
                          </div>
                          <div className="bg-green-500/10 p-1 rounded-full">
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="mb-8">
                  <h3 className="block text-sm font-medium mb-3">Select Extraction Schema</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-primary/5 rounded-lg border border-primary/10 p-4">
                    {/* Left column - Schema list */}
                    <div className="space-y-2">
                      {schemas.map((schema) => (
                        <div
                          key={schema.id}
                          className={cn(
                            "p-3 rounded-lg cursor-pointer transition-all duration-200 flex items-center justify-between",
                            selectedSchema === schema.id
                              ? "bg-primary text-primary-foreground"
                              : "bg-background/80 hover:bg-primary/10 border border-primary/10",
                            hoveredSchema === schema.id && selectedSchema !== schema.id && "border-primary/30",
                          )}
                          onClick={() => handleSchemaSelect(schema.id)}
                          onMouseEnter={() => handleSchemaHover(schema.id)}
                          onMouseLeave={() => handleSchemaHover(null)}
                        >
                          <div className="flex items-center gap-2">
                            <div
                              className={cn(
                                "w-8 h-8 rounded-md flex items-center justify-center",
                                selectedSchema === schema.id ? "bg-white/20" : "bg-primary/10",
                              )}
                            >
                              <FileSpreadsheet
                                className={cn("h-4 w-4", selectedSchema === schema.id ? "text-white" : "text-primary")}
                              />
                            </div>
                            <div>
                              <p className="font-medium text-sm">{schema.name}</p>
                              <p className="text-xs opacity-80">{schema.fields.length} fields</p>
                            </div>
                          </div>
                          {selectedSchema === schema.id && (
                            <div className="h-5 w-5 rounded-full bg-white/20 flex items-center justify-center">
                              <CheckCircle className="h-3 w-3 text-white" />
                            </div>
                          )}
                        </div>
                      ))}
                    </div>

                    {/* Right column - Schema fields */}
                    <div className="bg-background/50 rounded-lg border border-primary/10 p-3">
                      {hoveredSchema || selectedSchema ? (
                        <div className="h-full">
                          <div className="flex items-center gap-2 mb-2 pb-2 border-b border-primary/10">
                            <FileSpreadsheet className="h-4 w-4 text-primary" />
                            <h3 className="text-sm font-medium">
                              {getActiveSchema()?.name} Fields
                            </h3>
                          </div>
                          <div className="space-y-1">
                            {getActiveSchema()?.fields.map((field) => (
                              <div
                                key={field}
                                className="py-1 flex items-center gap-2 text-xs font-mono text-muted-foreground"
                              >
                                <span className="text-primary">•</span>
                                <span>{field}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <div className="h-full flex items-center justify-center text-center p-4">
                          <div className="text-muted-foreground text-sm">
                            <p>Select or hover over a schema</p>
                            <p className="text-xs mt-1">to view its fields</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="mt-auto">
                  <Button
                    className="w-full flex items-center gap-2 h-12"
                    onClick={handleSubmit}
                    disabled={!selectedFile || !selectedSchema}
                  >
                    <span>Process Document</span>
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ) : (
              <div
                className="p-2 h-full flex items-center justify-center cursor-pointer hover:bg-primary/5 transition-colors"
                onClick={handleReset}
              >
                <div className="rotate-180">
                  <ChevronRight className="h-6 w-6 text-primary" />
                </div>
              </div>
            )}
          </div>

          {/* Second Column - Processing or Results */}
          <div
            className={cn(
              "transition-all duration-500 ease-in-out rounded-xl glass-card relative",
              step === "upload" ? "md:w-1/3" : step === "processing" ? "md:w-full" : "md:w-5/6",
            )}
          >
            {step === "processing" ? (
              <div className="h-full flex items-center justify-center">
                <LoadingSpinner text="Processing document..." />
              </div>
            ) : step === "results" && extractionResult ? (
              <div className="h-full flex flex-col md:flex-row">
                {/* PDF Viewer */}
                <div className="md:w-1/2 h-full border-r border-primary/10">
                  <div className="p-6 border-b border-primary/10">
                    <h2 className="text-xl font-bold mb-1">Annotated Document</h2>
                    <p className="text-sm text-muted-foreground">The document with extracted fields highlighted</p>
                  </div>
                  <div className="h-[calc(100%-5rem)]">
                    <PDFViewer 
                      pdfFilename={extractionResult.annotated_pdf}
                      extractedFields={extractionResult.extracted_data}
                    />
                  </div>
                </div>

                {/* Extracted Data */}
                <div className="md:w-1/2 h-full overflow-auto">
                  <div className="p-6 border-b border-primary/10 sticky top-0 bg-background/90 backdrop-blur-sm z-10">
                    <h2 className="text-xl font-bold mb-1">Extracted Data</h2>
                    <p className="text-sm text-muted-foreground">
                      {extractionResult.schema} – {Object.keys(extractionResult.extracted_data).length} fields extracted
                    </p>
                  </div>
                  <div className="p-6">
                    <ExtractedDataTable data={extractionResult.extracted_data} />
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center p-6 text-center text-muted-foreground">
                <div>
                  <FileText className="h-16 w-16 mx-auto mb-4 opacity-20" />
                  <p>Upload a document and select a schema to begin</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  )
}

