import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Shield, Zap, FileSearch } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="px-6 py-4 flex justify-between items-center border-b border-border/40 backdrop-blur-md sticky top-0 z-50">
        <div className="font-bold text-2xl tracking-tighter flex items-center gap-2">
          <Shield className="h-6 w-6 text-primary" />
          <span>Plag<span className="text-primary">X</span></span>
        </div>
        <nav className="flex gap-4">
          <Link href="/login">
            <Button variant="ghost">Login</Button>
          </Link>
          <Link href="/signup">
            <Button>Get Started</Button>
          </Link>
        </nav>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-6 py-24 text-center">
        <div className="max-w-3xl space-y-8">
          <div className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80">
            Enterprise Grade AI Analysis
          </div>
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight">
            Uncover the <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-blue-600">Truth</span> in Text.
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Advanced plagiarism detection powered by semantic AI. 
            Identify exact matches, paraphrasing, and source origins with pinpoint accuracy.
          </p>
          <div className="flex justify-center gap-4 pt-4">
            <Link href="/signup">
              <Button size="lg" className="h-12 px-8 text-base">Start Scanning Now</Button>
            </Link>
            <Link href="/login">
              <Button size="lg" variant="outline" className="h-12 px-8 text-base">Dashboard Login</Button>
            </Link>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mt-32 text-left">
          <div className="p-6 rounded-2xl bg-card border">
            <FileSearch className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-xl font-bold mb-2">Deep Semantic Search</h3>
            <p className="text-muted-foreground">Goes beyond exact word matching to find paraphrased content using advanced sentence embeddings.</p>
          </div>
          <div className="p-6 rounded-2xl bg-card border">
            <Zap className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-xl font-bold mb-2">Lightning Fast</h3>
            <p className="text-muted-foreground">Processes large academic papers in seconds with our optimized vector search architecture.</p>
          </div>
          <div className="p-6 rounded-2xl bg-card border">
            <Shield className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-xl font-bold mb-2">Enterprise Security</h3>
            <p className="text-muted-foreground">Your documents are processed securely and isolated. We don't train our models on your data.</p>
          </div>
        </div>
      </main>
    </div>
  );
}
