"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { FileText, AlertTriangle, TrendingUp, Upload, ArrowRight, BarChart3, Clock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import api from "@/lib/api";
import type { DashboardStats } from "@/lib/types";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } };
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } };

function riskColor(level: string) {
  switch (level) {
    case "low": return "text-green-500";
    case "moderate": return "text-yellow-500";
    case "suspicious": return "text-orange-500";
    case "high": return "text-red-500";
    default: return "text-muted-foreground";
  }
}

function riskBadge(level: string) {
  switch (level) {
    case "low": return <Badge variant="outline" className="border-green-500/30 text-green-500 bg-green-500/10">Low Risk</Badge>;
    case "moderate": return <Badge variant="outline" className="border-yellow-500/30 text-yellow-500 bg-yellow-500/10">Moderate</Badge>;
    case "suspicious": return <Badge variant="outline" className="border-orange-500/30 text-orange-500 bg-orange-500/10">Suspicious</Badge>;
    case "high": return <Badge variant="outline" className="border-red-500/30 text-red-500 bg-red-500/10">High Risk</Badge>;
    default: return <Badge variant="outline">Unknown</Badge>;
  }
}

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/dashboard/stats")
      .then((res) => setStats(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}><CardContent className="p-6"><Skeleton className="h-16 w-full" /></CardContent></Card>
          ))}
        </div>
        <Card><CardContent className="p-6"><Skeleton className="h-48 w-full" /></CardContent></Card>
      </div>
    );
  }

  const statCards = [
    { title: "Total Documents", value: stats?.total_documents ?? 0, icon: FileText, color: "text-blue-500", bg: "bg-blue-500/10" },
    { title: "Total Reports", value: stats?.total_reports ?? 0, icon: BarChart3, color: "text-purple-500", bg: "bg-purple-500/10" },
    { title: "Avg. Similarity", value: `${stats?.average_score?.toFixed(1) ?? 0}%`, icon: TrendingUp, color: "text-orange-500", bg: "bg-orange-500/10" },
    { title: "High Risk", value: stats?.high_risk_count ?? 0, icon: AlertTriangle, color: "text-red-500", bg: "bg-red-500/10" },
  ];

  return (
    <motion.div className="space-y-6" variants={container} initial="hidden" animate="show">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((s) => (
          <motion.div key={s.title} variants={item}>
            <Card className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{s.title}</p>
                    <p className="text-3xl font-bold mt-1">{s.value}</p>
                  </div>
                  <div className={`h-12 w-12 rounded-xl ${s.bg} flex items-center justify-center`}>
                    <s.icon className={`h-6 w-6 ${s.color}`} />
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Quick Upload + Recent Reports */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Upload */}
        <motion.div variants={item}>
          <Card className="h-full">
            <CardHeader><CardTitle className="text-lg">Quick Upload</CardTitle></CardHeader>
            <CardContent className="flex flex-col items-center justify-center py-8 space-y-4">
              <div className="h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center">
                <Upload className="h-8 w-8 text-primary" />
              </div>
              <p className="text-sm text-muted-foreground text-center">Upload a document to start plagiarism analysis</p>
              <Button onClick={() => router.push("/upload")} className="gap-2">
                Upload Document <ArrowRight className="h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        </motion.div>

        {/* Recent Reports */}
        <motion.div variants={item} className="lg:col-span-2">
          <Card className="h-full">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Recent Reports</CardTitle>
              <Link href="/documents" className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "gap-1")}>
                View All <ArrowRight className="h-3 w-3" />
              </Link>
            </CardHeader>
            <CardContent>
              {!stats?.recent_reports?.length ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Clock className="h-10 w-10 mx-auto mb-3 opacity-50" />
                  <p>No reports yet. Upload a document to get started.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {stats.recent_reports.map((r: any) => (
                    <Link key={r.id} href={`/report/${r.id}`}>
                      <div className="flex items-center justify-between p-3 rounded-lg hover:bg-muted/50 transition-colors cursor-pointer">
                        <div className="flex items-center gap-3 min-w-0">
                          <FileText className="h-5 w-5 text-muted-foreground flex-shrink-0" />
                          <div className="min-w-0">
                            <p className="text-sm font-medium truncate">{r.document_name}</p>
                            <p className="text-xs text-muted-foreground">{new Date(r.created_at).toLocaleDateString()}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3 flex-shrink-0">
                          <span className={`text-lg font-bold ${riskColor(r.risk_level)}`}>{r.overall_score}%</span>
                          {riskBadge(r.risk_level)}
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </motion.div>
  );
}
