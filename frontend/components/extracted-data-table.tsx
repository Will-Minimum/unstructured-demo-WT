import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Calendar, DollarSign, Building, Clock, ShoppingCart } from "lucide-react"

interface ExtractedDataTableProps {
  data: Record<string, any>
}

export default function ExtractedDataTable({ data }: ExtractedDataTableProps) {
  const getIcon = (key: string) => {
    if (key.toLowerCase().includes("date")) return <Calendar className="h-4 w-4 text-blue-500" />
    if (key.toLowerCase().includes("amount") || key.toLowerCase().includes("price"))
      return <DollarSign className="h-4 w-4 text-green-500" />
    if (key.toLowerCase().includes("vendor") || key.toLowerCase().includes("merchant"))
      return <Building className="h-4 w-4 text-primary" />
    if (key.toLowerCase().includes("due")) return <Clock className="h-4 w-4 text-amber-500" />
    if (key.toLowerCase().includes("item")) return <ShoppingCart className="h-4 w-4 text-indigo-500" />
    return null
  }

  // Get the value from a complex data object or return the value directly if it's a primitive
  const getValue = (dataObj: any) => {
    if (dataObj && typeof dataObj === 'object' && 'value' in dataObj) {
      return dataObj.value;
    }
    return dataObj;
  }

  // Get confidence from the object if available, otherwise use the simulated confidence
  const getConfidence = (key: string, dataObj: any) => {
    if (dataObj && typeof dataObj === 'object' && 'confidence' in dataObj) {
      return dataObj.confidence;
    }
    
    // Fall back to simulated confidence
    if (key.includes("Vendor") || key.includes("Total")) return 0.98;
    if (key.includes("Date")) return 0.95;
    if (key.includes("Tax")) return 0.87;
    if (key.includes("Line")) return 0.92;
    return 0.90;
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.95) return "bg-green-500";
    if (confidence >= 0.85) return "bg-blue-500";
    if (confidence >= 0.75) return "bg-amber-500";
    return "bg-gray-500";
  }

  const getConfidencePercentage = (confidence: number) => {
    return `${Math.round(confidence * 100)}%`;
  }

  const renderValue = (key: string, dataObj: any) => {
    const value = getValue(dataObj);
    
    if (Array.isArray(value)) {
      return (
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="items" className="border-primary/10">
            <AccordionTrigger className="text-sm py-2 hover:no-underline">
              <div className="flex items-center gap-2">
                <ShoppingCart className="h-4 w-4 text-indigo-500" />
                <span>View {value.length} items</span>
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <div className="rounded-lg overflow-hidden border border-primary/10">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-primary/5 hover:bg-primary/10">
                      {Object.keys(value[0]).map((header) => (
                        <TableHead key={header} className="text-xs font-medium text-primary">
                          {header}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {value.map((item, idx) => (
                      <TableRow key={idx} className="hover:bg-primary/5">
                        {Object.values(item).map((cellValue, cellIdx) => (
                          <TableCell key={cellIdx} className="text-xs py-2">
                            {cellValue as string}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      )
    }

    // Handle date fields
    if (key.toLowerCase().includes("date") && typeof value === "string") {
      return (
        <div className="flex items-center gap-2">
          <span className="font-medium">{value}</span>
          <Badge
            variant="outline"
            className="text-xs bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800"
          >
            <Calendar className="h-3 w-3 mr-1" />
            Date
          </Badge>
        </div>
      )
    }

    // Handle amount fields
    if ((key.toLowerCase().includes("amount") || key.toLowerCase().includes("price")) && typeof value === "string") {
      return (
        <div className="flex items-center gap-2">
          <span className="font-medium">{value}</span>
          <Badge
            variant="outline"
            className="text-xs bg-green-50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800"
          >
            <DollarSign className="h-3 w-3 mr-1" />
            Amount
          </Badge>
        </div>
      )
    }

    return <span className="font-medium">{value}</span>
  }

  return (
    <div className="overflow-auto h-full rounded-lg border border-primary/10">
      <Table>
        <TableHeader className="bg-primary/5">
          <TableRow className="hover:bg-primary/10">
            <TableHead className="w-1/3 font-medium text-primary">Field</TableHead>
            <TableHead className="font-medium text-primary">Value</TableHead>
            <TableHead className="w-24 text-right font-medium text-primary">Confidence</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {Object.entries(data).map(([key, value]) => {
            const confidence = getConfidence(key, value);
            const confidencePercentage = getConfidencePercentage(confidence);
            const confidenceColor = getConfidenceColor(confidence);
            
            return (
              <TableRow key={key} className="hover:bg-primary/5">
                <TableCell className="font-medium flex items-center gap-2">
                  {getIcon(key)}
                  <span>{key}</span>
                </TableCell>
                <TableCell>{renderValue(key, value)}</TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    <div className="w-16 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className={confidenceColor}
                        style={{ width: confidencePercentage }}
                      ></div>
                    </div>
                    <span className="text-xs font-medium">{confidencePercentage}</span>
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  )
}

