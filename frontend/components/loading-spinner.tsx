"use client"

import { useEffect, useState } from "react"

interface LoadingSpinnerProps {
  text?: string
}

export default function LoadingSpinner({ text = "Loading..." }: LoadingSpinnerProps) {
  const [mounted, setMounted] = useState(false)
  
  useEffect(() => {
    setMounted(true)
  }, [])
  
  if (!mounted) return null
  
  return (
    <div className="flex flex-col items-center justify-center space-y-4">
      <div className="relative h-24 w-24">
        <div className="absolute inset-0 rounded-full border-t-4 border-primary opacity-25 animate-spin" 
             style={{ animationDuration: '1s' }} />
        <div className="absolute inset-0 rounded-full border-t-4 border-r-4 border-primary animate-spin"
             style={{ animationDuration: '1.5s' }} />
        <div className="absolute inset-2 rounded-full border-t-4 border-primary opacity-50 animate-spin"
             style={{ animationDuration: '2s', animationDirection: 'reverse' }} />
        <div className="absolute inset-4 rounded-full border-t-4 border-r-4 border-l-4 border-primary opacity-75 animate-spin"
             style={{ animationDuration: '3s', animationDirection: 'reverse' }} />
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="h-10 w-10 rounded-full bg-primary/10 backdrop-blur-sm flex items-center justify-center">
            <div className="h-5 w-5 rounded-full bg-primary"></div>
          </div>
        </div>
      </div>
      <p className="text-center text-sm font-medium text-muted-foreground">{text}</p>
    </div>
  )
}

