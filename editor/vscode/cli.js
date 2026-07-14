/* Pure CLI resolution helpers — no vscode import (unit-testable).
 *
 * Security (#45 adversarial fix): never build shell command strings from
 * user input. Callers must spawn with argv + shell:false / Task API.
 */
"use strict";

const path = require("path");
const fs = require("fs");

/**
 * @deprecated Prefer resolveCli().argv — kept only for display/debug labels.
 * Does NOT make shell-safe strings for user-controlled input.
 */
function quote(s) {
  // Escape for display only; never use for shell execution of untrusted input.
  return JSON.stringify(String(s));
}

/**
 * @param {object} opts
 * @param {string} opts.workspaceRoot
 * @param {string} [opts.pythonPath]
 * @param {string} [opts.cliPath]
 * @param {string} [opts.pythonPathExtra]
 * @param {string[]} opts.args
 * @param {NodeJS.ProcessEnv} [opts.env]
 * @returns {{ argv: string[], cwd: string, env: NodeJS.ProcessEnv, display: string }}
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
  /** @type {string[]} */
  let argv;
  if (cliPath) {
    argv = [cliPath, ...opts.args];
  } else {
    argv = [python, "-m", "designmd_pptx", ...opts.args];
  }
  // Display form is JSON-quoted for human terminals only — never pass to a shell.
  const display = argv.map((a) => JSON.stringify(String(a))).join(" ");
  return { argv, cwd: root, env, display, shellCmd: display };
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

/**
 * Detect shell metacharacters that would be dangerous if argv were joined into a shell.
 * Used by unit tests; runtime never shells user args.
 * @param {string} s
 */
function hasShellMeta(s) {
  return /[$`;&|<>(){}!]/.test(String(s));
}

module.exports = { quote, resolveCli, diagnosticsFromReport, hasShellMeta };
