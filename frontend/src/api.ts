import type { Meta } from "./types";

const TOKEN_KEY = "visionboard_token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* stockage indisponible : la session ne survivra pas au rechargement */
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function formatDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => (d && typeof d === "object" && "msg" in d ? String(d.msg) : String(d))).join(" · ");
  }
  return "Erreur inattendue";
}

export const SERVER_DOWN =
  "Le serveur de Vision Board ne répond pas. Lancez l'application avec « demarrer.bat » (double-clic) ou la " +
  "commande « npm start » à la racine du projet, puis réessayez.";

/** fetch, avec un message compréhensible quand le serveur (API) n'est pas démarré. */
async function request(url: string, init: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    throw new ApiError(0, SERVER_DOWN);
  }
  // Le serveur de l'interface répond 502/504 quand l'API derrière lui est arrêtée.
  if (res.status === 502 || res.status === 503 || res.status === 504) throw new ApiError(res.status, SERVER_DOWN);
  return res;
}

interface Options {
  method?: string;
  body?: unknown;
  form?: FormData;
}

export async function api<T>(path: string, options: Options = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (options.form) body = options.form;
  else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const res = await request(`/api${path}`, { method: options.method ?? (body ? "POST" : "GET"), headers, body });
  if (res.status === 401 && token) {
    setToken(null);
    window.location.assign("/login");
  }
  if (!res.ok) {
    let message = `Erreur ${res.status}`;
    try {
      message = formatDetail((await res.json()).detail);
    } catch {
      /* réponse non JSON */
    }
    throw new ApiError(res.status, message);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

let metaPromise: Promise<Meta> | null = null;

export function loadMeta(): Promise<Meta> {
  metaPromise ??= api<Meta>("/meta");
  return metaPromise;
}

export function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : "Erreur inattendue";
}

/** Télécharge un fichier protégé par l'authentification (export PDF / Word). */
export async function downloadFile(path: string, fallbackName: string): Promise<void> {
  const token = getToken();
  const res = await request(`/api${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!res.ok) {
    let message = `Erreur ${res.status}`;
    try {
      message = formatDetail((await res.json()).detail);
    } catch {
      /* réponse non JSON */
    }
    throw new ApiError(res.status, message);
  }
  const match = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") ?? "");
  const url = URL.createObjectURL(await res.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = match?.[1] ?? fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
