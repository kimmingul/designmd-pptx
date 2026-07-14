/* Pure CLI resolution helpers — no vscode import (unit-testable). */
"use strict";

const path = require("path");
const fs = require("fs");

function quote(s) {
  if (/[\s"]/g.test(String(s))) {
    return `"${String(s).replace(/"/g, '\\"')}"`;
  }
  return String(s);
}

/**
 * @param {object} opts
 * @param {string} opts.workspaceRoot
 * @param {string} [opts.pythonPath]
 * @param {string} [opts.cliPath]
 * @param {string} [opts.pythonPathExtra]
 * @param {string[]} opts.args
 * @param {NodeJS.ProcessEnv} [opts.env]
 */
function resolveCli(opts) {
  const root = opts.workspaceRoot || process.cwd();
  const python =
    opts.pythonPath || (process.platform === "win32" ? "python" : "python3");
  const cliPath = (opts.cliPath || "").trim();
  const extra = (opts.pythonPathExtra || "").trim();
  const env = { ...(opts.env || process.env) };
  const pyCandidates = [
    extra,
    path.join(root, "python"),
    path.join(root, "designmd-pptx", "python"),
  ].filter((p) => p && fs.existsSync(p));
  if (pyCandidates.length) {
    env.PYTHONPATH = [pyCandidates[0], env.PYTHONPATH || ""]
      .filter(Boolean)
      .join(path.delimiter);
  }
  let shellCmd;
  if (cliPath) {
    shellCmd = [quote(cliPath), ...opts.args.map(quote)].join(" ");
  } else {
    shellCmd = [quote(python), "-m", "designmd_pptx", ...opts.args.map(quote)].join(
      " ",
    );
  }
  return { shellCmd, cwd: root, env };
}

/**
 * Map a11y/refine/gate3 JSON → diagnostic-like objects for tests / Problems panel.
 * @param {object} data
 * @returns {{ severity: string, message: string, line: number }[]}
 */
function diagnosticsFromReport(data) {
  const diags = [];
  if (!data || typeof data !== "object") return diags;
  if (Array.isArray(data.findings)) {
    for (const f of data.findings) {
      const severity =
        f.severity === "error" ? "error" : f.severity === "warn" || f.severity === "warning" ? "warn" : "info";
      const line = typeof f.slide === "number" && f.slide > 0 ? f.slide - 1 : 0;
      diags.push({
        severity,
        message: `[${f.code || "finding"}] ${f.message || ""}`,
        line,
      });
    }
  }
  if (Array.isArray(data.history)) {
    for (const h of data.history) {
      for (const p of h.patches || []) {
        diags.push({
          severity: "info",
          message: `refine r${h.round}: ${p.action} (${p.code || ""})`,
          line: Math.max(0, (p.slide || 1) - 1),
        });
      }
    }
  }
  if (data.ok === false || data.pass === false) {
    diags.push({
      severity: "error",
      message: "Report marked fail/ok=false",
      line: 0,
    });
  }
  return diags;
}

module.exports = { quote, resolveCli, diagnosticsFromReport };
