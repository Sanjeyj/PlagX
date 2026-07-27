"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Download, FileText, ArrowLeft, Info, Eye, EyeOff, ShieldAlert, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import api from "@/lib/api";
import type { Report, HighlightSpan, MatchedSource } from "@/lib/types";

const SOURCE_COLORS = [
  "#EF4444", "#F97316", "#EAB308", "#22C55E", "#3B82F6",
  "#8B5CF6", "#EC4899", "#14B8A6", "#F43F5E", "#6366F1",
];

function ScoreGauge({ score, size = 150, label = "Similarity" }: { score: number; size?: number; label?: string }) {
  const radius = (size - 16) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  
  const color = score === 0 ? "#3b82f6" : score < 25 ? "#22C55E" : score < 50 ? "#EAB308" : score < 75 ? "#F97316" : "#EF4444";

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="currentColor" strokeWidth="8" className="text-muted/10" />
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={color} strokeWidth="8"
          strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" className="transition-all duration-1000" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-extrabold tracking-tight" style={{ color }}>{score}%</span>
        <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground mt-1">{label}</span>
      </div>
    </div>
  );
}

export default function ReportPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const reportId = params.id as string;
  const byDoc = searchParams.get("by") === "doc";
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeSource, setActiveSource] = useState<number | null>(null);
  const [selectedSpan, setSelectedSpan] = useState<HighlightSpan | null>(null);
  const [filterGroup, setFilterGroup] = useState<string | null>(null);
  const [showExcluded, setShowExcluded] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    const endpoint = byDoc ? `/report-by-document/${reportId}` : `/report/${reportId}`;
    api.get(endpoint)
      .then((res) => setReport(res.data))
      .catch(() => toast.error("Failed to load report"))
      .finally(() => setLoading(false));
  }, [reportId, byDoc]);

  // Poll report status if PDF is currently generating
  useEffect(() => {
    if (!report || report.pdf_status !== "generating") return;

    const intervalId = setInterval(async () => {
      try {
        const endpoint = byDoc ? `/report-by-document/${reportId}` : `/report/${reportId}`;
        const res = await api.get(endpoint);
        setReport(res.data);
        if (res.data.pdf_status !== "generating") {
          clearInterval(intervalId);
        }
      } catch (err) {
        console.error("Error polling report status", err);
      }
    }, 3000);

    return () => clearInterval(intervalId);
  }, [report?.pdf_status, reportId, byDoc]);

  // Filter highlights based on selection
  const filteredHighlights = useMemo(() => {
    if (!report) return [];
    let h = report.highlights;
    
    // Filter by active source
    if (activeSource !== null) {
      h = h.filter((s) => s.source_index === activeSource);
    }
    
    // Filter by match group
    if (filterGroup) {
      h = h.filter((s) => s.group_type === filterGroup);
    }
    
    // Toggle showing excluded (properly cited & quoted, or boilerplate)
    if (!showExcluded) {
      h = h.filter((s) => s.group_type !== "cited_and_quoted" && s.group_type !== "boilerplate");
    }
    
    return h;
  }, [report, activeSource, filterGroup, showExcluded]);

  // Aggregate ALL sources including overlapping ones
  const allSourcesList = useMemo(() => {
    if (!report) return [];
    const mainSources = [...report.matched_sources];
    const sourceMap: Record<string, { name: string; percentage: number; isOverlapping: boolean; color: string; index: number }> = {};
    
    // Add main sources
    mainSources.forEach((src) => {
      sourceMap[src.source_name] = {
        name: src.source_name,
        percentage: src.match_percentage,
        isOverlapping: false,
        color: src.color || SOURCE_COLORS[src.source_index % SOURCE_COLORS.length],
        index: src.source_index,
      };
    });

    // Extract overlapping sources from highlights
    report.highlights.forEach((h) => {
      if (h.overlapping_sources) {
        h.overlapping_sources.forEach((osrc) => {
          if (!sourceMap[osrc.source_name]) {
            sourceMap[osrc.source_name] = {
              name: osrc.source_name,
              percentage: osrc.similarity * 100,
              isOverlapping: true,
              color: osrc.source_index !== undefined && osrc.source_index >= 0 
                ? SOURCE_COLORS[osrc.source_index % SOURCE_COLORS.length]
                : "#9ca3af",
              index: osrc.source_index ?? -1,
            };
          }
        });
      }
    });

    return Object.values(sourceMap).sort((a, b) => b.percentage - a.percentage);
  }, [report]);

  const handleDownloadPdf = async () => {
    if (downloading) return;
    setDownloading(true);
    try {
      const id = report?.id || reportId;
      const res = await api.get(`/report/${id}/pdf`, { responseType: "blob" });
      
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `PlagX_Report_${report?.document_name || "document"}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("PDF downloaded successfully");
    } catch (err: any) {
      console.error(err);
      
      // Parse the JSON error details from the Blob response
      if (err.response && err.response.data instanceof Blob) {
        try {
          const text = await err.response.data.text();
          const errorJson = JSON.parse(text);
          const errorDetail = errorJson.detail;
          
          if (err.response.status === 409) {
            toast.info("PDF is currently generating. Polling for updates...");
            if (report) {
              setReport({ ...report, pdf_status: "generating" });
            }
          } else {
            toast.error(typeof errorDetail === "string" ? errorDetail : "PDF download failed");
          }
        } catch (parseErr) {
          toast.error("PDF download failed");
        }
      } else {
        toast.error("PDF download failed");
      }
    } finally {
      setDownloading(false);
    }
  };

  const getGroupLabel = (group?: string) => {
    switch (group) {
      case "uncited_overlap": return "Uncited Overlap";
      case "missing_quotation": return "Missing Quotation Marks";
      case "missing_citation": return "Missing Citation";
      case "cited_and_quoted": return "Cited and Quoted (Excluded)";
      case "weak_overlap": return "Weak Overlap";
      case "boilerplate": return "Common Boilerplate (Excluded)";
      case "ai_writing": return "AI Writing";
      default: return "Similarity Match";
    }
  };

  const getGroupDescription = (group?: string) => {
    switch (group) {
      case "uncited_overlap": return "Matching text that contains no quotation marks or inline citations nearby. High risk of plagiarism.";
      case "missing_quotation": return "Text matches verbatim and has an inline citation, but is missing quotation marks. Needs verbatim delimiters.";
      case "missing_citation": return "Text is enclosed in quotation marks, but no inline citation was found nearby. Needs source attribution.";
      case "cited_and_quoted": return "Content is properly enclosed in quotation marks and cited. Excluded from similarity scoring.";
      case "weak_overlap": return "Paraphrased match with lower semantic confidence. Safe/low risk.";
      case "boilerplate": return "Standard academic phrases or methods boilerplate. Excluded from similarity scoring.";
      case "ai_writing": return "Content classified as highly likely generated by an AI writing assistant.";
      default: return "";
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-4 gap-4">{[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24" />)}</div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (!report) return <div className="text-center py-20 text-muted-foreground">Report not found</div>;

  const riskColor = 
    report.risk_level === "none" ? "text-blue-500" :
    report.risk_level === "low" ? "text-green-500" : 
    report.risk_level === "moderate" ? "text-yellow-500" : 
    report.risk_level === "significant" ? "text-orange-500" : 
    "text-red-500";

  const renderHighlightedText = () => {
    const fullText = report.full_text;
    const highlights = filteredHighlights;
    
    if (!fullText) return <p className="text-muted-foreground text-sm">No text available.</p>;
    if (!highlights.length) {
      return fullText.split("\n").map((p, i) => p.trim() ? <p key={i} className="mb-4 leading-relaxed text-sm text-foreground/90">{p}</p> : null);
    }

    const sorted = [...highlights].sort((a, b) => a.start_char - b.start_char);
    const parts: React.ReactNode[] = [];
    let lastPos = 0;

    sorted.forEach((h, i) => {
      const start = Math.max(h.start_char, lastPos);
      if (start >= h.end_char) return;

      if (start > lastPos) {
        parts.push(<span key={`t-${i}`} className="text-foreground/90">{fullText.slice(lastPos, start)}</span>);
      }

      const isSelected = selectedSpan?.start_char === h.start_char && selectedSpan?.end_char === h.end_char;
      const srcColor = h.source_index >= 0 ? SOURCE_COLORS[h.source_index % SOURCE_COLORS.length] : "#8b5cf6";
      const isActive = activeSource === null || activeSource === h.source_index;

      const cleanHex = srcColor.replace("#", "");
      const r = parseInt(cleanHex.substring(0, 2), 16);
      const g = parseInt(cleanHex.substring(2, 4), 16);
      const b = parseInt(cleanHex.substring(4, 6), 16);
      
      let bg = `rgba(${r}, ${g}, ${b}, 0.12)`;
      let border = `2px solid ${srcColor}`;
      
      if (h.group_type === "cited_and_quoted" || h.group_type === "boilerplate") {
        bg = "rgba(229, 231, 235, 0.4)";
        border = "none";
      } else if (h.group_type === "weak_overlap") {
        bg = "transparent";
        border = "none";
      } else if (h.group_type === "missing_quotation") {
        border = "2px solid #F97316";
      } else if (h.group_type === "missing_citation") {
        border = "2px solid #EAB308";
      }

      if (isSelected) {
        bg = `rgba(${r}, ${g}, ${b}, 0.25)`;
      }

      parts.push(
        <span key={`h-${i}`} 
          className="relative group inline cursor-pointer transition-all duration-200 hover:brightness-95"
          style={{
            backgroundColor: isActive ? bg : "transparent",
            borderBottom: isActive ? border : "none",
            opacity: isActive ? 1 : 0.35,
          }}
          onClick={() => setSelectedSpan(isSelected ? null : h)}
        >
          {fullText.slice(start, h.end_char)}
          {isActive && h.source_index >= 0 && (
            <sup className="font-bold ml-0.5 text-[9px] pointer-events-none select-none animate-fade-in" style={{ color: srcColor }}>
              {h.source_index + 1}
            </sup>
          )}
        </span>
      );
      lastPos = h.end_char;
    });

    if (lastPos < fullText.length) {
      parts.push(<span key="end" className="text-foreground/90">{fullText.slice(lastPos)}</span>);
    }

    return (
      <div className="leading-relaxed text-sm whitespace-pre-wrap font-sans">
        {parts}
      </div>
    );
  };

  return (
    <motion.div className="space-y-6" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4 border-b pb-4">
        <div className="flex items-center gap-3">
          <Link href="/documents" className={cn(buttonVariants({ variant: "ghost", size: "icon" }), "rounded-full hover:bg-muted")}>
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <h2 className="text-xl font-bold flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              {report.document_name}
            </h2>
            <p className="text-xs text-muted-foreground">Processed {new Date(report.created_at).toLocaleString()}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {report.pdf_status === "failed" && (
            <Badge variant="destructive" className="font-bold text-xs px-2.5 py-1 bg-red-100 text-red-700 hover:bg-red-100">
              PDF Failed
            </Badge>
          )}
          <Badge variant="outline" className={`capitalize font-bold text-xs px-2.5 py-1 ${riskColor} bg-muted/40`}>
            {report.risk_level} Similarity Risk
          </Badge>
          <Button 
            onClick={handleDownloadPdf} 
            disabled={downloading || report.pdf_status === "generating"}
            size="sm" 
            className="gap-2 rounded-full font-semibold shadow-sm"
          >
            {report.pdf_status === "generating" || downloading ? (
              <span className="flex items-center gap-1.5">
                <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                {report.pdf_status === "generating" ? "Generating..." : "Downloading..."}
              </span>
            ) : (
              <>
                <Download className="h-4 w-4" /> Download PDF
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Main Scoring Section */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <Card className="lg:col-span-1 flex flex-col items-center justify-center p-6 bg-gradient-to-br from-background to-muted/20 border shadow-sm">
          <ScoreGauge score={report.overall_score} size={150} label="Similarity Index" />
        </Card>
        
        <Card className="lg:col-span-3 grid grid-cols-2 sm:grid-cols-4 gap-4 p-6 bg-background border shadow-sm">
          {[
            { label: "AI Content Probability", value: `${report.ai_score || 0}%`, sub: report.ai_confidence, color: "text-purple-500" },
            { label: "Primary Sources", value: report.total_sources, sub: "Indexed Matches", color: "text-blue-500" },
            { label: "Analyzed Words", value: report.total_words, sub: `${report.total_pages} Pages`, color: "text-emerald-500" },
            { label: "Overlapping Words", value: report.matched_words, sub: "Deduplicated Coverage", color: "text-amber-500" },
          ].map((stat, idx) => (
            <div key={idx} className="flex flex-col justify-center border-r last:border-r-0 pr-4 pl-2">
              <span className="text-2xl font-extrabold tracking-tight text-foreground">{stat.value}</span>
              <span className="text-[10px] font-bold text-muted-foreground uppercase mt-1 tracking-wider">{stat.label}</span>
              <span className="text-[10px] text-muted-foreground mt-0.5">{stat.sub}</span>
            </div>
          ))}
        </Card>
      </div>

      {/* Interactive Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar panels */}
        <Card className="lg:col-span-1 flex flex-col h-[650px] shadow-sm border overflow-hidden">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex flex-col h-full">
            <TabsList className="grid grid-cols-3 rounded-none border-b h-11 p-0 bg-muted/30">
              <TabsTrigger value="overview" className="text-xs h-full rounded-none">Overview</TabsTrigger>
              <TabsTrigger value="sources" className="text-xs h-full rounded-none">All Sources</TabsTrigger>
              <TabsTrigger value="groups" className="text-xs h-full rounded-none">Groups</TabsTrigger>
            </TabsList>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {/* Match Overview Panel */}
              <TabsContent value="overview" className="m-0 space-y-3">
                <div className="flex items-center justify-between text-xs text-muted-foreground pb-1">
                  <span>Top Attributed Sources</span>
                  <button onClick={() => { setActiveSource(null); setFilterGroup(null); }} className="hover:text-primary underline">Clear Filter</button>
                </div>
                {report.matched_sources.map((src) => {
                  const color = src.color || SOURCE_COLORS[src.source_index % SOURCE_COLORS.length];
                  const isFiltered = activeSource === src.source_index;
                  return (
                    <button
                      key={src.source_index}
                      className={`w-full text-left p-2.5 rounded-lg border transition-all flex items-center gap-2.5 ${
                        isFiltered ? "bg-primary/5 border-primary" : "bg-card border-border hover:bg-muted/40"
                      }`}
                      onClick={() => setActiveSource(isFiltered ? null : src.source_index)}
                    >
                      <span className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0" style={{ backgroundColor: color }}>
                        {src.source_index + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold truncate text-foreground">{src.source_name}</p>
                        <p className="text-[10px] text-muted-foreground">Top match region contribution</p>
                      </div>
                      <span className="text-xs font-bold font-mono" style={{ color }}>{src.match_percentage}%</span>
                    </button>
                  );
                })}
                {report.matched_sources.length === 0 && (
                  <p className="text-xs text-muted-foreground text-center py-8">No sources matched.</p>
                )}
              </TabsContent>

              {/* All Sources Panel */}
              <TabsContent value="sources" className="m-0 space-y-2">
                <p className="text-[11px] text-muted-foreground pb-1">Complete source list including overlapping and secondary matches.</p>
                {allSourcesList.map((src, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 rounded-lg border bg-card text-xs">
                    <span className="flex items-center gap-2 truncate">
                      <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: src.color }} />
                      <span className="truncate max-w-[150px] font-medium">{src.name}</span>
                      {src.isOverlapping && <Badge variant="outline" className="text-[8px] h-4 py-0 px-1 border-muted">Overlap</Badge>}
                    </span>
                    <span className="font-semibold font-mono text-muted-foreground">{src.percentage.toFixed(1)}%</span>
                  </div>
                ))}
              </TabsContent>

              {/* Match Groups Panel */}
              <TabsContent value="groups" className="m-0 space-y-3">
                <div className="flex items-center justify-between text-xs text-muted-foreground pb-1">
                  <span>Match Severity Groups</span>
                  <button onClick={() => setFilterGroup(null)} className="hover:text-primary underline">Reset</button>
                </div>
                
                {[
                  { id: "uncited_overlap", label: "Uncited Overlaps", color: "bg-red-500" },
                  { id: "missing_quotation", label: "Missing Quotation Marks", color: "bg-orange-500" },
                  { id: "missing_citation", label: "Missing Citations", color: "bg-yellow-500" },
                  { id: "weak_overlap", label: "Weak Semantic Overlaps", color: "bg-amber-400" },
                  { id: "cited_and_quoted", label: "Cited & Quoted (Excluded)", color: "bg-slate-400" },
                  { id: "boilerplate", label: "Boilerplate (Excluded)", color: "bg-gray-300" },
                ].map((grp) => {
                  const count = report.highlights.filter((h) => h.group_type === grp.id).length;
                  const isFiltered = filterGroup === grp.id;
                  
                  return (
                    <button
                      key={grp.id}
                      className={`w-full text-left p-2 rounded-lg border transition-all flex items-center justify-between text-xs ${
                        isFiltered ? "bg-primary/5 border-primary font-medium" : "bg-card border-border hover:bg-muted/40"
                      }`}
                      onClick={() => setFilterGroup(isFiltered ? null : grp.id)}
                    >
                      <span className="flex items-center gap-2 truncate">
                        <span className={`w-2 h-2 rounded-full ${grp.color}`} />
                        <span className="truncate">{grp.label}</span>
                      </span>
                      <Badge variant="secondary" className="text-[10px]">{count}</Badge>
                    </button>
                  );
                })}
              </TabsContent>
            </div>
          </Tabs>
        </Card>

        {/* Document Viewer panel */}
        <Card className="lg:col-span-3 flex flex-col h-[650px] shadow-sm border overflow-hidden">
          <CardHeader className="pb-2 border-b bg-muted/10 flex flex-row items-center justify-between h-14 p-4">
            <div className="flex items-center gap-2">
              <CardTitle className="text-sm font-bold text-foreground">Document Viewer</CardTitle>
              <CardDescription className="text-xs hidden sm:inline">Click highlighted areas to analyze sources</CardDescription>
            </div>
            
            <div className="flex items-center gap-4 text-xs">
              <label className="flex items-center gap-1.5 cursor-pointer text-muted-foreground select-none">
                <input 
                  type="checkbox" 
                  checked={showExcluded} 
                  onChange={(e) => {
                    setShowExcluded(e.target.checked);
                    if (!e.target.checked && (filterGroup === "cited_and_quoted" || filterGroup === "boilerplate")) {
                      setFilterGroup(null);
                    }
                  }} 
                  className="rounded text-primary focus:ring-0 border-muted"
                />
                Show Excluded Items
              </label>
            </div>
          </CardHeader>
          
          <CardContent className="flex-1 overflow-hidden flex flex-col p-0">
            {/* Legend Panel */}
            <div className="flex gap-4 p-3 border-b text-[10px] font-semibold text-muted-foreground bg-muted/5 flex-wrap justify-center select-none">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded" style={{ background: "rgba(239,68,68,0.12)", border: "1px solid #EF4444" }} />
                Uncited Overlap
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded" style={{ background: "rgba(249,115,22,0.12)", border: "1px solid #F97316" }} />
                Missing Quotations
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded" style={{ background: "rgba(234,179,8,0.12)", border: "1px solid #EAB308" }} />
                Missing Citation
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded border border-dashed border-amber-400 bg-amber-100/10" />
                Weak Overlap
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded bg-gray-200 border border-gray-300" />
                Excluded Cite/Boilerplate
              </span>
            </div>

            <div className="flex-1 overflow-y-auto p-6 font-serif select-text">
              {renderHighlightedText()}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Selected Match Details Popover */}
      <AnimatePresence>
        {selectedSpan && (
          <motion.div 
            initial={{ opacity: 0, y: 15 }} 
            animate={{ opacity: 1, y: 0 }} 
            exit={{ opacity: 0, y: 15 }}
            className="fixed bottom-6 right-6 z-50 max-w-sm w-full"
          >
            <Card className="shadow-2xl border-primary bg-card/95 backdrop-blur-md">
              <CardHeader className="pb-2 border-b flex flex-row justify-between items-start">
                <div>
                  <Badge variant="outline" className="text-[10px] font-bold text-primary mb-1 uppercase tracking-wider">
                    {getGroupLabel(selectedSpan.group_type)}
                  </Badge>
                  <CardTitle className="text-sm font-bold truncate pr-6">{selectedSpan.source_name}</CardTitle>
                </div>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => setSelectedSpan(null)} 
                  className="rounded-full w-6 h-6 p-0 hover:bg-muted absolute top-2 right-2"
                >
                  &times;
                </Button>
              </CardHeader>
              <CardContent className="pt-3 space-y-2 text-xs">
                <p className="text-muted-foreground italic leading-relaxed">
                  "{selectedSpan.matched_text.length > 120 ? selectedSpan.matched_text.slice(0, 120) + '...' : selectedSpan.matched_text}"
                </p>
                <div className="bg-muted/40 p-2.5 rounded-lg border space-y-1">
                  <p className="font-semibold text-foreground">Classification Details</p>
                  <p className="text-muted-foreground leading-normal">{getGroupDescription(selectedSpan.group_type)}</p>
                </div>
                
                {selectedSpan.overlapping_sources && selectedSpan.overlapping_sources.length > 0 && (
                  <div className="space-y-1">
                    <p className="font-semibold text-muted-foreground text-[10px] uppercase tracking-wider">Additional Overlapping Sources</p>
                    <div className="max-h-20 overflow-y-auto space-y-1">
                      {selectedSpan.overlapping_sources.map((osrc, idx) => (
                        <div key={idx} className="flex justify-between items-center py-0.5 border-b last:border-b-0">
                          <span className="truncate max-w-[200px] text-muted-foreground">{osrc.source_name}</span>
                          <span className="font-mono text-muted-foreground">{(osrc.similarity * 100).toFixed(0)}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Collapsible Details Section at bottom */}
      <Card className="border shadow-sm">
        <CardHeader className="pb-3 border-b bg-muted/5">
          <CardTitle className="text-sm font-bold text-foreground">Detailed Breakdown & Analytics</CardTitle>
        </CardHeader>
        <CardContent className="pt-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                <ShieldAlert className="h-4 w-4 text-purple-500" /> AI Content Analysis
              </p>
              <div className="space-y-2 bg-muted/20 border p-4 rounded-xl">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-muted-foreground">Confidence Class</span>
                  <span className="font-bold text-purple-500">{report.ai_confidence}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-muted-foreground">Calculated Prob.</span>
                  <span className="font-bold">{report.ai_score}%</span>
                </div>
                <div className="text-[10px] text-muted-foreground pt-1 leading-normal border-t mt-1">
                  Our neural classifier estimates the probability of text fragments being synthesized by LLM agents.
                </div>
              </div>
            </div>

            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                <Info className="h-4 w-4 text-blue-500" /> Match Engine Breakdown
              </p>
              <div className="space-y-3 bg-muted/20 border p-4 rounded-xl text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Exact Match Component</span>
                  <span className="font-mono font-semibold">{report.exact_score}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Semantic Paraphrase</span>
                  <span className="font-mono font-semibold">{report.semantic_score}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Source Diversity Metric</span>
                  <span className="font-mono font-semibold">{report.source_density_score}%</span>
                </div>
              </div>
            </div>

            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Integrity Flags
              </p>
              <div className="bg-muted/20 border p-4 rounded-xl text-xs h-[106px] overflow-y-auto space-y-1.5">
                {report.integrity_flags && report.integrity_flags.length > 0 ? (
                  report.integrity_flags.map((flag, idx) => (
                    <div key={idx} className="flex gap-2 text-red-500">
                      <span>&bull;</span>
                      <span className="leading-snug">{flag}</span>
                    </div>
                  ))
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground italic text-xs">
                    No integrity anomalies detected
                  </div>
                )}
              </div>
            </div>
          </div>

          {report.paragraph_scores && report.paragraph_scores.length > 0 && (
            <div className="border-t pt-6 space-y-3">
              <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Paragraph-by-Paragraph Similarity Index</p>
              <div className="grid grid-cols-2 sm:grid-cols-5 md:grid-cols-10 gap-2">
                {report.paragraph_scores.map((ps) => (
                  <div 
                    key={ps.paragraph_index} 
                    className="p-2 border rounded-lg bg-background text-center flex flex-col justify-between h-14"
                  >
                    <span className="text-[10px] text-muted-foreground">§{ps.paragraph_index + 1}</span>
                    <span className={`text-xs font-bold ${
                      ps.score > 50 ? "text-red-500" :
                      ps.score > 25 ? "text-orange-500" :
                      ps.score > 10 ? "text-yellow-500" :
                      "text-emerald-500"
                    }`}>{ps.score}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
