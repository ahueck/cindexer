import * as fs from 'fs';
import {randomUUID} from 'node:crypto';
import * as path from 'path';
import * as vscode from 'vscode';

import {CompilationDatabaseProvider} from './compilationDatabaseProvider';

export class StatePublisher {
  public readonly sessionId: string;
  public readonly sessionDir: string;
  private readonly statePath: string;
  private readonly activeSessionPath: string;

  constructor(
      private readonly baseDir: string,
      private readonly dbProvider: CompilationDatabaseProvider) {
    this.sessionId = randomUUID();
    this.sessionDir = path.join(baseDir, 'sessions', this.sessionId);
    this.statePath = path.join(this.sessionDir, 'vscode_state.json');
    this.activeSessionPath = path.join(baseDir, 'active_session');

    if (!fs.existsSync(this.sessionDir)) {
      fs.mkdirSync(this.sessionDir, {recursive: true});
    }
  }

  public async publishState(): Promise<void> {
    const activeEditor = vscode.window.activeTextEditor;
    const activeFilePath = activeEditor?.document.uri.fsPath;
    const workspaceFolder = activeEditor ?
        vscode.workspace.getWorkspaceFolder(activeEditor.document.uri) :
        vscode.workspace.workspaceFolders?.[0];

    const state = {
      schemaVersion: 1,
      sessionId: this.sessionId,
      timestamp: Date.now(),
      activeFile: activeFilePath || null,
      languageId: activeEditor?.document.languageId || null,
      workspaceFolder: workspaceFolder?.uri.fsPath || null,
      windowFocused: vscode.window.state.focused,
      compilationDatabasePath:
          await this.dbProvider.getCompilationDatabasePath(activeFilePath)
    };

    // Atomic write via temp file
    const tmpPath = `${this.statePath}.tmp`;
    fs.writeFileSync(tmpPath, JSON.stringify(state, null, 2) + '\n');
    fs.renameSync(tmpPath, this.statePath);

    fs.writeFileSync(this.activeSessionPath, this.sessionId);
  }

  public dispose(): void {
    try {
      if (fs.existsSync(this.sessionDir)) {
        fs.rmSync(this.sessionDir, {recursive: true, force: true});
      }
    } catch (e) {
    }
  }
}
