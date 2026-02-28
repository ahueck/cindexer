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
      schema_version: 1,
      session_id: this.sessionId,
      timestamp: Date.now(),
      active_file: activeFilePath || null,
      language_id: activeEditor?.document.languageId || null,
      workspace_folder: workspaceFolder?.uri.fsPath || null,
      window_focused: vscode.window.state.focused,
      compilation_database_path:
          await this.dbProvider.getCompilationDatabasePath(activeFilePath)
    };

    // Atomic write via temp file
    const tmpStatePath = `${this.statePath}.tmp`;
    await fs.promises.writeFile(
        tmpStatePath, JSON.stringify(state, null, 2) + '\n');
    await fs.promises.rename(tmpStatePath, this.statePath);

    const tmpSessionPath = `${this.activeSessionPath}.tmp`;
    await fs.promises.writeFile(tmpSessionPath, this.sessionId);
    await fs.promises.rename(tmpSessionPath, this.activeSessionPath);
  }

  public dispose(): void {
    try {
      if (fs.existsSync(this.activeSessionPath)) {
        const currentActive =
            fs.readFileSync(this.activeSessionPath, 'utf-8').trim();
        if (currentActive === this.sessionId) {
          fs.rmSync(this.activeSessionPath, {force: true});
        }
      }

      if (fs.existsSync(this.sessionDir)) {
        fs.rmSync(this.sessionDir, {recursive: true, force: true});
      }
    } catch (e) {
      // Ignored
    }
  }
}
