"use client";

import { useState } from "react";
import { AlertCircle, Globe, Loader2 } from "lucide-react";
import { AnalysisError, extractUrl } from "@/lib/api-client";
import { Button } from "@/components/ui/button";

type Props = {
  onExtracted: (text: string, sourceReference: string) => void;
  disabled?: boolean;
};

export function UrlInput({ onExtracted, disabled }: Props) {
  const [url, setUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event?: React.FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    if (!url.trim() || disabled) return;
    setError(null);
    setIsLoading(true);
    try {
      const result = await extractUrl(url.trim());
      onExtracted(result.text, result.source_reference);
    } catch (err) {
      if (err instanceof AnalysisError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unbekannter Fehler beim Laden der URL.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form
      onSubmit={submit}
      className="flex h-[240px] flex-col items-center justify-center gap-3 px-6"
    >
      <Globe className="h-6 w-6 text-muted-foreground" aria-hidden />
      <p className="text-center text-sm text-foreground">
        URL der Landingpage / Produktseite einfügen
      </p>
      <p className="text-center text-xs text-muted-foreground">
        Bilder und Grafiken werden im MVP nicht analysiert (folgt mit OCR in V1.1).
      </p>
      <div className="flex w-full max-w-md items-center gap-2">
        <input
          type="url"
          inputMode="url"
          placeholder="https://shop.deinemarke.de/produkte/magnesium"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={disabled || isLoading}
          required
          className="flex-1 rounded-md border border-border/60 bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/70 outline-none focus:border-primary focus:ring-1 focus:ring-primary disabled:opacity-60"
        />
        <Button
          type="submit"
          size="sm"
          disabled={disabled || isLoading || !url.trim()}
        >
          {isLoading ? (
            <>
              <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" aria-hidden />
              Lade…
            </>
          ) : (
            "Text laden"
          )}
        </Button>
      </div>
      {error && (
        <div className="flex w-full max-w-md items-start gap-2 rounded-md border border-status-forbidden/30 bg-status-forbidden-bg/40 px-3 py-2 text-xs text-status-forbidden">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          <span>{error}</span>
        </div>
      )}
    </form>
  );
}
