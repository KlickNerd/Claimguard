"use client";

import { useRef, useState } from "react";
import {
  AlertCircle,
  FileText,
  Loader2,
  Upload,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { AnalysisError, extractPdf } from "@/lib/api-client";

const MAX_BYTES = 10 * 1024 * 1024;

type Props = {
  onExtracted: (text: string, sourceReference: string) => void;
  disabled?: boolean;
};

export function PdfDropzone({ onExtracted, disabled }: Props) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filename, setFilename] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleFile = async (file: File) => {
    setError(null);
    if (file.type && file.type !== "application/pdf") {
      setError("Bitte eine PDF-Datei wählen.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setError("Die Datei ist größer als 10 MB.");
      return;
    }

    setFilename(file.name);
    setIsUploading(true);
    try {
      const result = await extractPdf(file);
      onExtracted(result.text, result.source_reference);
    } catch (err) {
      if (err instanceof AnalysisError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unbekannter Fehler bei der PDF-Extraktion.");
      }
      setFilename(null);
    } finally {
      setIsUploading(false);
    }
  };

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;
    const file = e.dataTransfer.files?.[0];
    if (file) void handleFile(file);
  };

  const onPick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) void handleFile(file);
    e.target.value = "";
  };

  const reset = () => {
    setFilename(null);
    setError(null);
  };

  return (
    <div className="flex h-[240px] flex-col items-center justify-center px-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        className={cn(
          "flex h-full w-full cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border/70 px-6 text-center transition-colors",
          isDragging && "border-primary bg-primary/5",
          disabled && "cursor-not-allowed opacity-60",
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={onPick}
          disabled={disabled || isUploading}
        />
        {isUploading ? (
          <>
            <Loader2 className="h-6 w-6 animate-spin text-primary" aria-hidden />
            <p className="text-sm text-foreground">
              {filename ?? "PDF wird verarbeitet…"}
            </p>
            <p className="text-xs text-muted-foreground">
              Text wird extrahiert, gleich kannst du ihn prüfen.
            </p>
          </>
        ) : filename && !error ? (
          <>
            <FileText className="h-6 w-6 text-primary" aria-hidden />
            <p className="text-sm font-medium text-foreground">{filename}</p>
            <p className="text-xs text-muted-foreground">
              Text steht oben im Editor – prüfe und passe ihn ggf. an.
            </p>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                reset();
              }}
              className="mt-1 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            >
              <X className="h-3 w-3" aria-hidden />
              Andere Datei wählen
            </button>
          </>
        ) : (
          <>
            <Upload className="h-6 w-6 text-muted-foreground" aria-hidden />
            <p className="text-sm text-foreground">
              PDF hierher ziehen oder zum Auswählen klicken
            </p>
            <p className="text-xs text-muted-foreground">
              Max. 10 MB · text-basierte PDFs · gescannte Dokumente werden im MVP nicht unterstützt
            </p>
          </>
        )}
      </div>

      {error && (
        <div className="mt-2 flex w-full items-start gap-2 rounded-md border border-status-forbidden/30 bg-status-forbidden-bg/40 px-3 py-2 text-xs text-status-forbidden">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
