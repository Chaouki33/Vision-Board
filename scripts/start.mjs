// Lance Vision Board en une commande : l'API (port 8000) et l'interface (port 5173).
// Utilisation, depuis la racine du projet :  npm start      (Ctrl+C pour tout arrêter)
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const windows = process.platform === "win32";
const python = join(root, "backend", ".venv", windows ? "Scripts/python.exe" : "bin/python");

if (!existsSync(python)) {
  console.error("Environnement Python introuvable : suivez l'installation du README (dossier backend, .venv).");
  process.exit(1);
}
if (!existsSync(join(root, "frontend", "node_modules"))) {
  console.error("Dépendances de l'interface absentes : lancez « npm install » dans le dossier frontend.");
  process.exit(1);
}

const services = [
  { name: "API", color: "\x1b[36m", cmd: python, args: ["-m", "uvicorn", "app.main:app", "--port", "8000"], cwd: join(root, "backend") },
  { name: "Interface", color: "\x1b[33m", cmd: windows ? "npm.cmd" : "npm", args: ["run", "dev"], cwd: join(root, "frontend") },
];

const children = services.map(({ name, color, cmd, args, cwd }) => {
  const child = spawn(cmd, args, { cwd, shell: windows && cmd.endsWith(".cmd"), env: { ...process.env, FORCE_COLOR: "1" } });
  const prefix = `${color}[${name}]\x1b[0m `;
  const relay = (stream) => (data) =>
    data.toString().split(/\r?\n/).filter(Boolean).forEach((line) => stream.write(prefix + line + "\n"));
  child.stdout.on("data", relay(process.stdout));
  child.stderr.on("data", relay(process.stderr));
  child.on("exit", (code) => {
    console.log(`${prefix}arrêté (code ${code ?? 0})`);
    stopAll();
  });
  return child;
});

let stopping = false;
function stopAll() {
  if (stopping) return;
  stopping = true;
  for (const child of children) {
    if (child.exitCode !== null) continue;
    // Sous Windows, npm lance un sous-processus : on arrête toute l'arborescence.
    if (windows) spawn("taskkill", ["/pid", String(child.pid), "/t", "/f"], { stdio: "ignore" });
    else child.kill("SIGTERM");
  }
  setTimeout(() => process.exit(0), 500);
}
process.on("SIGINT", stopAll);
process.on("SIGTERM", stopAll);

console.log("\nVision Board démarre… ouvrez \x1b[1mhttp://localhost:5173\x1b[0m (Ctrl+C pour arrêter)\n");
