import { Scan } from "lucide-react"
import ThemeSwitcher from "@/components/theme-switcher"

export default function Navbar() {
  return (
    <div className="fixed top-0 left-0 right-0 z-50 border-b border-border/40 bg-background/80 backdrop-blur-md">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Logo placeholder - replace with your company logo */}
          <div className="w-8 h-8 bg-primary/10 rounded-md flex items-center justify-center">
            {/* This is where you'll insert your logo later */}
            <Scan className="h-5 w-5 text-primary" />
          </div>

          <h1 className="text-xl font-semibold">PDF Extractor</h1>
        </div>

        <ThemeSwitcher />
      </div>
    </div>
  )
}

