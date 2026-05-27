export interface MoveResponse {
  piece_index: number;
  rotation: number;
  row: number;
  col: number;
  score: number;
  lines_cleared: number;
}

export interface PieceRecommendation {
  piece_index: number;
  slot_label: string;
  piece_name: string | null;
  piece_shape: number[][] | null;
  move: MoveResponse | null;
  advice: string;
}

export interface AnalyzeResponse {
  board: number[][];
  board_rect: [number, number, number, number];
  pieces: (number[][] | null)[];
  piece_names: (string | null)[];
  best_move: MoveResponse | null;
  piece_recommendations: PieceRecommendation[];
  alternative_moves: MoveResponse[];
  summary: string | null;
  overlay_base64: string | null;
  message: string | null;
}

function apiBase(): string {
  const env = import.meta.env.VITE_API_URL;
  if (env) return env.replace(/\/$/, "");
  return "/api";
}

function formatApiDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) =>
        typeof d === "object" && d && "msg" in d
          ? String((d as { msg: string }).msg)
          : String(d)
      )
      .join(" ");
  }
  return "Analiz başarısız.";
}

export async function analyzeScreenshot(file: File): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("file", file);

  const url = `${apiBase()}/analyze?debug=1`;
  let res: Response;
  try {
    res = await fetch(url, { method: "POST", body: form });
  } catch {
    throw new Error(
      "API'ye bağlanılamadı. Backend çalışıyor mu? (backend klasöründe: uvicorn app.main:app --reload --port 8000)"
    );
  }

  if (!res.ok) {
    const text = await res.text();
    let detail = "Analiz başarısız.";
    try {
      const err = JSON.parse(text) as { detail?: unknown };
      detail = formatApiDetail(err.detail);
    } catch {
      if (res.status === 502 || res.status === 504) {
        detail =
          "API sunucusu kapalı veya yanıt vermiyor. Önce backend'i başlatın (port 8000), sonra sayfayı yenileyin.";
      } else if (text) {
        detail = `Sunucu hatası (${res.status}): ${text.slice(0, 120)}`;
      }
    }
    throw new Error(detail);
  }

  return res.json();
}
