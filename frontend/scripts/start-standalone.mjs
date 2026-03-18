import { existsSync } from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import process from "node:process";

// In the Docker image, Dockerfile copies .next/standalone/* → /app/
// so server.js is at /app/server.js (i.e. process.cwd()/server.js).
const serverEntry = path.resolve(process.cwd(), "server.js");

if (!existsSync(serverEntry)) {
  console.error(`Standalone server not found: ${serverEntry}`);
  process.exit(1);
}

const child = spawn(process.execPath, [serverEntry], {
  stdio: "inherit",
  env: process.env,
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }

  process.exit(code ?? 0);
});
