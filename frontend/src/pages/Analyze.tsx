import { useCallback, useEffect, useRef, useState } from "react";
import { analyzeScreenshot, type AnalyzeResponse } from "../api/analyze";
import { BoardGrid } from "../components/BoardGrid";

type Status = "idle" | "loading" | "done" | "error";

export function AnalyzePage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [preview, setPreview] = useState<string | null>(null);

  const runAnalysis = useCallback(async (file: File) => {
    setStatus("loading");
    setError(null);
    setResult(null);
    setPreview(URL.createObjectURL(file));

    try {
      const data = await analyzeScreenshot(file);
      setResult(data);
      setStatus("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Bilinmeyen hata");
      setStatus("error");
    }
  }, []);

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) void runAnalysis(file);
    e.target.value = "";
  };

  useEffect(() => {
    const base = import.meta.env.VITE_API_URL?.replace(/\/$/, "") ?? "/api";
    fetch(`${base}/health`)
      .then((r) => setApiOnline(r.ok))
      .catch(() => setApiOnline(false));
  }, []);

  return (
    <div className="analyze-page">
      <header>
        <h1>Block Blast Bot</h1>
        <p className="subtitle">Sıkıştığın yerde ekran görüntüsü yükle, en iyi hamleyi gör.</p>
      </header>

      {apiOnline === false && (
        <div className="alert error" role="status">
          API kapalı. Ayrı terminalde backend başlat:{" "}
          <code>cd backend → uvicorn app.main:app --reload --port 8000</code>
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={onFile}
      />

      <button
        type="button"
        className="btn-primary"
        disabled={status === "loading"}
        onClick={() => inputRef.current?.click()}
      >
        {status === "loading" ? "Analiz ediliyor…" : "Ekran görüntüsü yükle"}
      </button>

      <p className="tip">
        Tam ekran SS al: 8×8 tahta ve alttaki 3 taş görünsün.
      </p>

      {status === "loading" && <div className="spinner" aria-live="polite" />}

      {error && (
        <div className="alert error" role="alert">
          {error}
        </div>
      )}

      {result && status === "done" && (
        <section className="results">
          {result.message && !result.best_move && (
            <div className="alert warn">{result.message}</div>
          )}

          {result.summary && (
            <div className="move-card best-summary">
              <h2>En iyi hamle</h2>
              <p>{result.summary}</p>
            </div>
          )}

          {result.piece_recommendations?.length > 0 && (
            <div className="piece-recs">
              <h2>Her taş nereye konmalı?</h2>
              <p className="recs-hint">
                Block Blast’ta her turda <strong>bir</strong> taş kullanırsın. Aşağıda
                üç taşın da en iyi yeri — yeşil özet en yüksek skorlu hamle.
              </p>
              <ul className="rec-list">
                {result.piece_recommendations.map((rec) => (
                  <li
                    key={rec.piece_index}
                    className={
                      result.best_move?.piece_index === rec.piece_index
                        ? "rec-item rec-best"
                        : "rec-item"
                    }
                  >
                    <span className="rec-slot">{rec.slot_label}</span>
                    {rec.piece_name && (
                      <span className="rec-shape">{rec.piece_name}</span>
                    )}
                    <p className="rec-advice">{rec.advice}</p>
                    {rec.piece_shape && (
                      <pre className="shape-mini" aria-hidden>
                        {rec.piece_shape
                          .map((row) => row.map((c) => (c ? "■" : "·")).join(" "))
                          .join("\n")}
                      </pre>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <h3>Tahta</h3>
          <BoardGrid
            board={result.board}
            bestMove={result.best_move}
            pieceShape={
              result.best_move
                ? result.pieces[result.best_move.piece_index]
                : null
            }
          />

          {result.overlay_base64 && (
            <>
              <h3>Algılama önizlemesi</h3>
              <img
                className="overlay-img"
                src={`data:image/png;base64,${result.overlay_base64}`}
                alt="Tahta ve önerilen yerleşim"
              />
            </>
          )}

          {result.alternative_moves.length > 0 && (
            <details className="alts">
              <summary>Alternatif hamleler</summary>
              <ul>
                {result.alternative_moves.map((m, i) => (
                  <li key={i}>
                    Taş {m.piece_index + 1} — ({m.row + 1},{m.col + 1}) — skor{" "}
                    {Math.round(m.score)}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </section>
      )}

      {preview && status !== "loading" && (
        <img className="thumb" src={preview} alt="Yüklenen görüntü" />
      )}
    </div>
  );
}
