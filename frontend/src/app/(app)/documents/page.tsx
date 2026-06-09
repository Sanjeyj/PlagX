"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { FileText, Trash2, Eye, Clock, CheckCircle, Loader2, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import api from "@/lib/api";
import type { Document } from "@/lib/types";

function statusIcon(status: string) {
  switch (status) {
    case "completed": return <CheckCircle className="h-4 w-4 text-green-500" />;
    case "processing": return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
    case "failed": return <AlertCircle className="h-4 w-4 text-red-500" />;
    default: return <Clock className="h-4 w-4 text-muted-foreground" />;
  }
}

function statusBadge(status: string) {
  switch (status) {
    case "completed": return <Badge className="bg-green-500/10 text-green-500 border-green-500/30">Completed</Badge>;
    case "processing": return <Badge className="bg-blue-500/10 text-blue-500 border-blue-500/30">Processing</Badge>;
    case "failed": return <Badge className="bg-red-500/10 text-red-500 border-red-500/30">Failed</Badge>;
    default: return <Badge variant="outline">Pending</Badge>;
  }
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchDocs = () => {
    api.get("/documents").then((res) => setDocuments(res.data.documents)).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { fetchDocs(); }, []);

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this document?")) return;
    try {
      await api.delete(`/documents/${id}`);
      toast.success("Document deleted");
      fetchDocs();
    } catch { toast.error("Failed to delete"); }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => <Card key={i}><CardContent className="p-4"><Skeleton className="h-16 w-full" /></CardContent></Card>)}
      </div>
    );
  }

  return (
    <motion.div className="space-y-6" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">My Documents</h2>
          <p className="text-muted-foreground">{documents.length} document{documents.length !== 1 ? "s" : ""} uploaded</p>
        </div>
        <Link href="/upload"><Button className="gap-2">Upload New</Button></Link>
      </div>

      {documents.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-lg font-medium">No documents yet</p>
            <p className="text-muted-foreground mt-1">Upload a document to get started</p>
            <Link href="/upload"><Button className="mt-4">Upload Document</Button></Link>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {documents.map((doc, i) => (
            <motion.div key={doc.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
              <Card className="hover:shadow-sm transition-shadow">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <FileText className="h-5 w-5 text-primary" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-medium text-sm truncate">{doc.original_name}</p>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                          <span>{doc.file_type.toUpperCase().replace(".", "")}</span>
                          <span>•</span>
                          <span>{formatSize(doc.file_size)}</span>
                          <span>•</span>
                          <span>{new Date(doc.upload_date).toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0">
                      {statusBadge(doc.status)}
                      {doc.status === "completed" && (
                        <Link href={`/report/${doc.id}?by=doc`}>
                          <Button variant="outline" size="sm" className="gap-1"><Eye className="h-3 w-3" /> Report</Button>
                        </Link>
                      )}
                      <Button variant="ghost" size="icon" className="text-red-500 hover:text-red-600 h-8 w-8" onClick={() => handleDelete(doc.id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
