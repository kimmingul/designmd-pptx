/*---------------------------------------------------------------------------------------------
 * designmd-pptx VS Code / Cursor extension MVP (#45)
 * Thin shell over the designmd-pptx CLI — no OfficeCLI bundling.
 *--------------------------------------------------------------------------------------------*/
"use strict";

const vscode = require("vscode");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");
const { resolveCli: resolveCliPure, diagnosticsFromReport } = require("./cli");

const DIAG_COLLECTION = "designmd-pptx";

/** @param {vscode.ExtensionContext} context */
/** @type {vscode.OutputChannel | undefined} */
let sharedOutput;

function activate(context) {
  const diagnostics = vscode.languages.createDiagnosticCollection(DIAG_COLLECTION);
  context.subscriptions.push(diagnostics);
  sharedOutput = vscode.window.createOutputChannel("designmd-pptx");
  context.subscriptions.push(sharedOutput);

  const explorer = new DesignmdExplorer();
  context.subscriptions.push(
    vscode.window.registerTreeDataProvider("designmdPptx.explorer", explorer),
  );

  const cmds = {
    "designmdPptx.doctor": () => runCli(["doctor"], { reveal: true }),
    "designmdPptx.doctorInstall": () =>
      runCli(["doctor", "--install", "--dry-run"], { reveal: true }),
    "designmdPptx.compose": () => composeActive(explorer),
    "designmdPptx.scaffold": () => scaffoldActive(explorer),
    "designmdPptx.a11y": () => a11yActive(explorer, diagnostics),
    "designmdPptx.refine": () => refineActive(explorer, diagnostics),
    "designmdPptx.benchmark": () => {
      const out = workspaceOutput("benchmark-out");
      return runCli(["benchmark", "-o", out], { reveal: true });
    },
    "designmdPptx.openContactSheet": () => openGlob(["**/*.contact.png", "**/*contact*.png", "**/*.png"], "contact sheet"),
    "designmdPptx.openGate3Report": () =>
      openGlob(
        ["**/*.gate3.json", "**/refine.report.json", "**/a11y.report.json", "**/compose.report.json"],
        "report JSON",
      ),
    "designmdPptx.refreshExplorer": () => explorer.refresh(),
  };

  for (const [id, fn] of Object.entries(cmds)) {
    context.subscriptions.push(vscode.commands.registerCommand(id, fn));
  }

  // Watch report files → Problems panel
  const watcher = vscode.workspace.createFileSystemWatcher(
    "**/{a11y.report.json,refine.report.json,compose.report.json,*.gate3.json}",
  );
  const reload = (uri) => loadDiagnosticsFromReport(uri, diagnostics);
  watcher.onDidCreate(reload);
  watcher.onDidChange(reload);
  watcher.onDidDelete((uri) => diagnostics.delete(uri));
  context.subscriptions.push(watcher);

  // Seed diagnostics for existing reports
  vscode.workspace
    .findFiles("**/{a11y.report.json,refine.report.json,compose.report.json,*.gate3.json}", "**/node_modules/**", 40)
    .then((uris) => uris.forEach((u) => loadDiagnosticsFromReport(u, diagnostics)));
}

function deactivate() {}

// ── CLI resolution ──────────────────────────────────────────────────────────

function cfg() {
  return vscode.workspace.getConfiguration("designmdPptx");
}

function workspaceRoot() {
  const f = vscode.workspace.workspaceFolders?.[0];
  return f ? f.uri.fsPath : undefined;
}

function workspaceOutput(rel) {
  const root = workspaceRoot() || process.cwd();
  const base = cfg().get("outputDir") || "out/designmd";
  return path.join(root, base, rel);
}

/**
 * @param {string[]} args
 * @returns {{ argv: string[], cwd: string, env: NodeJS.ProcessEnv, display: string }}
 */
function resolveCli(args) {
  const root = workspaceRoot() || process.cwd();
  const c = cfg();
  return resolveCliPure({
    workspaceRoot: root,
    pythonPath: c.get("pythonPath") || "",
    cliPath: c.get("cliPath") || "",
    pythonPathExtra: c.get("pythonPathExtra") || "",
    args,
    env: process.env,
  });
}

/**
 * Run designmd-pptx with argv (shell:false) — never interpolates user input
 * into a shell string (adversarial #45 P1).
 * @param {string[]} args
 * @param {{ reveal?: boolean, title?: string }} [opts]
 * @returns {Thenable<void>}
 */
function runCli(args, opts = {}) {
  const { argv, cwd, env, display } = resolveCli(args);
  const name = opts.title || `designmd-pptx ${args[0] || ""}`.trim();
  const out = sharedOutput || vscode.window.createOutputChannel("designmd-pptx");
  if (opts.reveal !== false) {
    out.show(true);
  }
  out.appendLine(`$ ${display}`);
  const status = vscode.window.setStatusBarMessage(`$(sync~spin) ${name}`, 60000);

  return new Promise((resolve) => {
    const [cmd, ...cmdArgs] = argv;
    const child = spawn(cmd, cmdArgs, {
      cwd,
      env,
      shell: false,
      windowsHide: true,
    });
    child.stdout?.on("data", (buf) => out.append(buf.toString()));
    child.stderr?.on("data", (buf) => out.append(buf.toString()));
    child.on("error", (err) => {
      out.appendLine(`error: ${err.message}`);
      status.dispose();
      vscode.window.showErrorMessage(`designmd-pptx failed to start: ${err.message}`);
      resolve();
    });
    child.on("close", (code) => {
      out.appendLine(`\n[exit ${code}]`);
      status.dispose();
      if (code !== 0) {
        vscode.window.showWarningMessage(`${name} exited ${code} — see Output → designmd-pptx`);
      }
      resolve();
    });
  });
}

// ── Commands ────────────────────────────────────────────────────────────────

async function composeActive(explorer) {
  const uri = await pickFile(
    { "Markdown brief": ["md"] },
    "Select a markdown brief to compose",
  );
  if (!uri) return;
  const out = workspaceOutput("composed");
  await runCli(["compose", uri.fsPath, "-o", out, "--design", cfg().get("defaultDesign") || "default"], {
    title: "designmd-pptx compose",
  });
  explorer.refresh();
  vscode.window.showInformationMessage(`compose → ${out} (see terminal)`);
}

async function scaffoldActive(explorer) {
  let content;
  const active = vscode.window.activeTextEditor?.document.uri;
  if (active && /\.deck\.json$/i.test(active.fsPath)) {
    content = active.fsPath;
  } else {
    const uri = await pickFile(
      { "Deck-spec JSON": ["json"] },
      "Select content.deck.json (or cancel to scaffold without content)",
    );
    content = uri?.fsPath;
  }
  const design = cfg().get("defaultDesign") || "default";
  const out = workspaceOutput("scaffold");
  const args = ["scaffold", design, "-o", out];
  if (content) args.push("--content", content);
  await runCli(args, { title: "designmd-pptx scaffold" });
  explorer.refresh();
}

async function a11yActive(explorer, diagnostics) {
  let deck = await resolveDeckPath();
  if (!deck) return;
  const outDir = workspaceOutput("a11y");
  const report = path.join(outDir, "a11y.report.json");
  const design = cfg().get("defaultDesign") || "default";
  await runCli(
    ["a11y", "--design", design, "--content", deck, "-o", report, "--generate-missing"],
    { title: "designmd-pptx a11y" },
  );
  // Load when file appears (async terminal)
  setTimeout(() => {
    if (fs.existsSync(report)) {
      loadDiagnosticsFromReport(vscode.Uri.file(report), diagnostics);
      vscode.workspace.openTextDocument(report).then((d) => vscode.window.showTextDocument(d, { preview: true }));
    }
  }, 1500);
  explorer.refresh();
}

async function refineActive(explorer, diagnostics) {
  let deck = await resolveDeckPath();
  if (!deck) return;
  const feedback = await vscode.window.showInputBox({
    prompt: "Natural-language feedback (optional)",
    placeHolder: "too dense — split bullets",
  });
  const out = workspaceOutput("refined");
  const args = ["refine", deck, "-o", out, "--rounds", "3"];
  if (feedback) args.push("--feedback", feedback);
  await runCli(args, { title: "designmd-pptx refine" });
  const report = path.join(out, "refine.report.json");
  setTimeout(() => {
    if (fs.existsSync(report)) {
      loadDiagnosticsFromReport(vscode.Uri.file(report), diagnostics);
    }
  }, 1500);
  explorer.refresh();
}

async function resolveDeckPath() {
  const active = vscode.window.activeTextEditor?.document.uri;
  if (active && /\.json$/i.test(active.fsPath)) return active.fsPath;
  const uri = await pickFile({ "Deck-spec": ["json"] }, "Select content.deck.json");
  return uri?.fsPath;
}

async function pickFile(filters, title) {
  const uris = await vscode.window.showOpenDialog({
    canSelectMany: false,
    openLabel: "Select",
    filters,
    title,
    defaultUri: workspaceRoot() ? vscode.Uri.file(workspaceRoot()) : undefined,
  });
  return uris?.[0];
}

async function openGlob(patterns, label) {
  const root = workspaceRoot();
  if (!root) {
    vscode.window.showWarningMessage("Open a workspace folder first.");
    return;
  }
  /** @type {vscode.Uri[]} */
  let found = [];
  for (const p of patterns) {
    const hits = await vscode.workspace.findFiles(p, "**/node_modules/**", 20);
    found = found.concat(hits);
  }
  // Prefer out/ paths and newer names
  found = [...new Map(found.map((u) => [u.fsPath, u])).values()];
  if (!found.length) {
    vscode.window.showInformationMessage(`No ${label} found in workspace.`);
    return;
  }
  found.sort((a, b) => b.fsPath.localeCompare(a.fsPath));
  const pick =
    found.length === 1
      ? found[0]
      : await vscode.window.showQuickPick(
          found.map((u) => ({ label: path.basename(u.fsPath), description: u.fsPath, uri: u })),
          { placeHolder: `Open ${label}` },
        ).then((x) => x?.uri);
  if (pick) {
    if (/\.png$/i.test(pick.fsPath)) {
      await vscode.commands.executeCommand("vscode.open", pick);
    } else {
      const doc = await vscode.workspace.openTextDocument(pick);
      await vscode.window.showTextDocument(doc, { preview: true });
    }
  }
}

// ── Diagnostics from report JSON ────────────────────────────────────────────

function loadDiagnosticsFromReport(uri, collection) {
  try {
    const text = fs.readFileSync(uri.fsPath, "utf8");
    const data = JSON.parse(text);
    const mapped = diagnosticsFromReport(data);
    /** @type {vscode.Diagnostic[]} */
    const diags = mapped.map((d) => {
      const sev =
        d.severity === "error"
          ? vscode.DiagnosticSeverity.Error
          : d.severity === "warn"
            ? vscode.DiagnosticSeverity.Warning
            : vscode.DiagnosticSeverity.Information;
      return new vscode.Diagnostic(
        new vscode.Range(d.line, 0, d.line, 200),
        d.message,
        sev,
      );
    });
    // compose slide warnings
    if (Array.isArray(data.slides)) {
      for (const s of data.slides) {
        for (const w of s.warnings || []) {
          const line = Math.max(0, (s.index || 1) - 1);
          diags.push(
            new vscode.Diagnostic(
              new vscode.Range(line, 0, line, 120),
              `compose/extract: ${w}`,
              vscode.DiagnosticSeverity.Warning,
            ),
          );
        }
      }
    }
    collection.set(uri, diags);
  } catch {
    // ignore invalid JSON
  }
}

// ── Tree explorer ───────────────────────────────────────────────────────────

class DesignmdExplorer {
  constructor() {
    this._onDidChange = new vscode.EventEmitter();
    this.onDidChangeTreeData = this._onDidChange.event;
  }
  refresh() {
    this._onDidChange.fire(undefined);
  }
  getTreeItem(el) {
    return el;
  }
  async getChildren(el) {
    if (el) return el.children || [];
    const root = workspaceRoot();
    if (!root) {
      return [infoItem("Open a folder to scan for DESIGN.md / deck-spec files")];
    }
    const groups = [
      await groupFiles("DESIGN.md", "**/DESIGN.md", "**/node_modules/**"),
      await groupFiles("Deck-specs (*.deck.json)", "**/*.deck.json", "**/node_modules/**"),
      await groupFiles("Briefs (*.md under briefs/)", "**/briefs/**/*.md", "**/node_modules/**"),
      await groupFiles("Reports", "**/{a11y.report.json,refine.report.json,compose.report.json,*.gate3.json}", "**/node_modules/**"),
    ];
    return groups.filter(Boolean);
  }
}

async function groupFiles(label, pattern, exclude) {
  const uris = await vscode.workspace.findFiles(pattern, exclude, 50);
  if (!uris.length) return null;
  const item = new vscode.TreeItem(label, vscode.TreeItemCollapsibleState.Expanded);
  item.contextValue = "group";
  item.children = uris
    .sort((a, b) => a.fsPath.localeCompare(b.fsPath))
    .map((u) => {
      const t = new vscode.TreeItem(path.basename(u.fsPath), vscode.TreeItemCollapsibleState.None);
      t.resourceUri = u;
      t.command = { command: "vscode.open", title: "Open", arguments: [u] };
      t.description = vscode.workspace.asRelativePath(u);
      t.contextValue = "file";
      return t;
    });
  return item;
}

function infoItem(msg) {
  const t = new vscode.TreeItem(msg, vscode.TreeItemCollapsibleState.None);
  t.iconPath = new vscode.ThemeIcon("info");
  return t;
}

module.exports = {
  activate,
  deactivate,
  resolveCli,
  loadDiagnosticsFromReport,
};
