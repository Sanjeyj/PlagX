"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, X, CheckCircle, Loader2, AlertCircle, ArrowRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import api from "@/lib/api";

type Stage = "idle" | "uploading" | "processing" | "done" | "error";

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [progress, setProgress] = useState(0);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [reportId, setReportId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [workerStage, setWorkerStage] = useState<string>("Initializing worker...");

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted.length > 0) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
    },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024,
  });

  const handleUpload = async () => {
    if (!file) return;
    setStage("uploading");
    setProgress(10);

    try {
      // Upload file
      const formData = new FormData();
      formData.append("file", file);
      const uploadRes = await api.post("/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (e) => {
          if (e.total) setProgress(Math.round((e.loaded / e.total) * 30));
        },
      });

      const docId = uploadRes.data.id;
      setDocumentId(docId);
      setProgress(35);
      setStage("processing");

      // Start plagiarism check
      await api.post(`/check/${docId}`);
      setProgress(40);

      // Poll for completion
      let attempts = 0;
      const maxAttempts = 300; // 5 minutes to allow for first-time AI model downloads
      while (attempts < maxAttempts) {
        await new Promise((r) => setTimeout(r, 1000));
        const statusRes = await api.get(`/check-status/${docId}`);
        const status = statusRes.data.status;
        const currentProgress = statusRes.data.progress;
        
        if (statusRes.data.worker_stage) {
          setWorkerStage(statusRes.data.worker_stage);
        }

        if (status === "completed") {
          setProgress(100);
          // Get report
          const reportRes = await api.get(`/report-by-document/${docId}`);
          setReportId(reportRes.data.id);
          setStage("done");
          toast.success("Plagiarism analysis complete!");
          return;
        } else if (status === "failed") {
          throw new Error(statusRes.data.message || "Analysis failed");
        }

        // Use actual backend progress if available, else fallback to fake progression
        if (currentProgress > 0) {
            setProgress(currentProgress);
        } else {
            setProgress(40 + Math.min(attempts * 0.5, 50));
        }
        
        attempts++;
      }

      throw new Error("Analysis timed out");
    } catch (err: any) {
      setStage("error");
      setErrorMsg(err.response?.data?.detail || err.message || "Upload failed");
      toast.error("Upload failed");
    }
  };

  const reset = () => {
    setFile(null);
    setStage("idle");
    setProgress(0);
    setDocumentId(null);
    setReportId(null);
    setErrorMsg("");
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <motion.div className="max-w-2xl mx-auto space-y-6" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
      <div>
        <h2 className="text-2xl font-bold">Upload Document</h2>
        <p className="text-muted-foreground mt-1">Upload a PDF, DOCX, or TXT file for plagiarism analysis</p>
      </div>

      <Card>
        <CardContent className="p-6">
          <AnimatePresence mode="wait">
            {stage === "idle" && (
              <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                {/* Drop Zone */}
                <div
                  {...getRootProps()}
                  className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
                    isDragActive ? "border-primary bg-primary/5" : "border-border hover:border-primary/50 hover:bg-muted/30"
                  }`}
                >
                  <input {...getInputProps()} />
                  <Upload className={`h-12 w-12 mx-auto mb-4 ${isDragActive ? "text-primary" : "text-muted-foreground"}`} />
                  {isDragActive ? (
                    <p className="text-primary font-medium">Drop your file here</p>
                  ) : (
                    <>
                      <p className="font-medium">Drag & drop your document here</p>
                      <p className="text-sm text-muted-foreground mt-1">or click to browse files</p>
                      <p className="text-xs text-muted-foreground mt-3">Supports PDF, DOCX, TXT • Max 50MB</p>
                    </>
                  )}
                </div>

                {/* File Preview */}
                {file && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-4 p-4 rounded-lg bg-muted/50 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <FileText className="h-8 w-8 text-primary" />
                      <div>
                        <p className="font-medium text-sm">{file.name}</p>
                        <p className="text-xs text-muted-foreground">{formatSize(file.size)}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="icon" onClick={(e) => { e.stopPropagation(); setFile(null); }}>
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </motion.div>
                )}

                {file && (
                  <Button className="w-full mt-4 h-12 text-base gap-2" onClick={handleUpload}>
                    Start Analysis <ArrowRight className="h-4 w-4" />
                  </Button>
                )}
              </motion.div>
            )}

            {(stage === "uploading" || stage === "processing") && (
              <motion.div key="processing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="py-12 text-center space-y-6">
                <Loader2 className="h-12 w-12 text-primary mx-auto animate-spin" />
                <div>
                  <p className="font-semibold text-lg">
                    {stage === "uploading" ? "Uploading document..." : workerStage}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    {stage === "processing" ? "Distributed workers are processing your document" : "Please wait..."}
                  </p>
                </div>
                <div className="max-w-xs mx-auto space-y-2">
                  <Progress value={progress} className="h-2" />
                  <p className="text-xs text-muted-foreground">{Math.round(progress)}% complete</p>
                </div>
              </motion.div>
            )}

            {stage === "done" && (
              <motion.div key="done" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="py-12 text-center space-y-6">
                <CheckCircle className="h-16 w-16 text-green-500 mx-auto" />
                <div>
                  <p className="font-semibold text-xl">Analysis Complete!</p>
                  <p className="text-muted-foreground mt-1">Your plagiarism report is ready to view</p>
                </div>
                <div className="flex gap-3 justify-center">
                  <Button onClick={() => reportId && router.push(`/report/${reportId}`)} className="gap-2">
                    View Report <ArrowRight className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" onClick={reset}>Upload Another</Button>
                </div>
              </motion.div>
            )}

            {stage === "error" && (
              <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="py-12 text-center space-y-6">
                <AlertCircle className="h-16 w-16 text-red-500 mx-auto" />
                <div>
                  <p className="font-semibold text-xl">Analysis Failed</p>
                  <p className="text-muted-foreground mt-1">{errorMsg}</p>
                </div>
                <Button onClick={reset} variant="outline">Try Again</Button>
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>
    </motion.div>
  );
}
