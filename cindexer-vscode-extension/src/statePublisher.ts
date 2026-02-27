import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { randomUUID } from 'node:crypto';

export class StatePublisher {
    public readonly sessionId: string;
    public readonly sessionDir: string;
    private readonly statePath: string;
    private readonly activeSessionPath: string;

    constructor(private readonly baseDir: string) {
        this.sessionId = randomUUID();
        this.sessionDir = path.join(baseDir, 'sessions', this.sessionId);
        this.statePath = path.join(this.sessionDir, 'vscode_state.json');
        this.activeSessionPath = path.join(baseDir, 'active_session');

        if (!fs.existsSync(this.sessionDir)) {
            fs.mkdirSync(this.sessionDir, { recursive: true });
        }
    }

    public publishState(): void {
        const activeEditor = vscode.window.activeTextEditor;
        const workspaceFolder = activeEditor 
            ? vscode.workspace.getWorkspaceFolder(activeEditor.document.uri)
            : vscode.workspace.workspaceFolders?.[0];

        const state = {
            schemaVersion: 1,
            sessionId: this.sessionId,
            timestamp: Date.now(),
            activeFile: activeEditor?.document.uri.fsPath || null,
            languageId: activeEditor?.document.languageId || null,
            workspaceFolder: workspaceFolder?.uri.fsPath || null,
            windowFocused: vscode.window.state.focused,
            compilationDatabasePath: this.findCompileCommands(activeEditor?.document.uri.fsPath)
        };

        // Atomic write via temp file
        const tmpPath = `${this.statePath}.tmp`;
        fs.writeFileSync(tmpPath, JSON.stringify(state, null, 2) + '\n');
        fs.renameSync(tmpPath, this.statePath);

        // Update global "active_session" pointer
        fs.writeFileSync(this.activeSessionPath, this.sessionId);
    }

    private findCompileCommands(activeFilePath?: string): string | null {
        if (!activeFilePath) { return null; }

        let currentDir = path.dirname(activeFilePath);
        const root = path.parse(currentDir).root;

        while (currentDir !== root) {
            const possiblePaths = [
                path.join(currentDir, 'compile_commands.json'),
                path.join(currentDir, 'build', 'compile_commands.json')
            ];

            for (const p of possiblePaths) {
                if (fs.existsSync(p)) {
                    return p;
                }
            }

            const parentDir = path.dirname(currentDir);
            if (parentDir === currentDir) { break; }
            currentDir = parentDir;
        }

        return null;
    }

    public dispose(): void {
        try {
            if (fs.existsSync(this.sessionDir)) {
                fs.rmSync(this.sessionDir, { recursive: true, force: true });
            }
            // If we were the active session, we could delete the pointer, 
            // but it's better to let it stay or let the next instance overwrite it.
        } catch (e) {
            // Best effort cleanup
        }
    }
}
