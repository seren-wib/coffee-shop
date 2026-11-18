// The client key is read from the development .env and injected at dev time.
// File: DOTENV_PATH, else the repository root .env, else the main checkout's .env
// when run from a git worktree (SDD 9). TOSS_CLIENT_KEY=test_ck_...
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");

function envFilePath() {
  if (process.env.DOTENV_PATH) return process.env.DOTENV_PATH;
  const local = resolve(repoRoot, ".env");
  if (existsSync(local)) return local;
  // A worktree has no .env of its own; use the main checkout's.
  const common = execFileSync(
    "git",
    ["rev-parse", "--path-format=absolute", "--git-common-dir"],
    { cwd: repoRoot, encoding: "utf8" },
  ).trim();
  return resolve(common, "..", ".env");
}

function readEnvFile(path) {
  const values = {};
  for (const line of readFileSync(path, "utf8").split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z_]+)\s*=\s*(.*?)\s*$/);
    if (m) values[m[1]] = m[2];
  }
  return values;
}

const env = readEnvFile(envFilePath());
if (!env.TOSS_CLIENT_KEY?.startsWith("test_")) {
  throw new Error("TOSS_CLIENT_KEY must be a test key (test_...)");
}

export default defineConfig({
  server: { host: "localhost", port: 5173, strictPort: true },
  define: { __TOSS_CLIENT_KEY__: JSON.stringify(env.TOSS_CLIENT_KEY) },
  build: {
    rollupOptions: {
      input: ["index.html", "success.html", "fail.html"],
    },
  },
});
