import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';

import {CMakeToolsApi, getCMakeToolsApi, Version} from './cmakeApi';

export class CompilationDatabaseProvider implements vscode.Disposable {
  private cmakeApi: CMakeToolsApi|undefined;
  private cachedDbPath: string|null = null;
  private lastScannedPath: string|null = null;
  private disposables: vscode.Disposable[] = [];

  private readonly _onDatabaseChanged = new vscode.EventEmitter<string|null>();
  public readonly onDatabaseChanged = this._onDatabaseChanged.event;

  public async getCompilationDatabasePath(activeFilePath?: string):
      Promise<string|null> {
    if (activeFilePath &&
        (!this.cachedDbPath || this.shouldRescan(activeFilePath))) {
      await this.updateCompilationDatabase(activeFilePath);
    }
    return this.cachedDbPath;
  }

  private shouldRescan(activeFilePath: string): boolean {
    if (!this.lastScannedPath) {
      return true;
    }
    // Rescan if the directory of the active file changed:
    // a. src/main.cpp to src/impl.cpp -> no rescan
    // b. src/main.cpp to lib/impl.cpp -> rescan
    // TODO might relax
    return path.dirname(activeFilePath) !== path.dirname(this.lastScannedPath);
  }

  private async getCMakeApi(): Promise<CMakeToolsApi|undefined> {
    if (!this.cmakeApi) {
      this.cmakeApi = await getCMakeToolsApi(Version.v1);
      if (this.cmakeApi) {
        this.disposables.push(
            this.cmakeApi.onActiveProjectChanged(() => this.updateAndNotify()));
        this.disposables.push(
            this.cmakeApi.onBuildTargetChanged(() => this.updateAndNotify()));
        this.disposables.push(
            this.cmakeApi.onLaunchTargetChanged(() => this.updateAndNotify()));
      }
    }
    return this.cmakeApi;
  }

  private async updateAndNotify(): Promise<void> {
    const activeEditor = vscode.window.activeTextEditor;
    const newPath =
        await this.updateCompilationDatabase(activeEditor?.document.uri.fsPath);
    this._onDatabaseChanged.fire(newPath);
  }

  public async updateCompilationDatabase(activeFilePath?: string):
      Promise<string|null> {
    if (!activeFilePath) {
      return this.cachedDbPath;
    }

    this.lastScannedPath = activeFilePath;

    // 1. Try CMake Tools API
    const api = await this.getCMakeApi();
    if (api) {
      try {
        const project = await api.getProject(vscode.Uri.file(activeFilePath));
        if (project) {
          const buildDir = await project.getBuildDirectory();
          if (buildDir) {
            const cmakeFile = path.join(buildDir, 'compile_commands.json');
            if (fs.existsSync(cmakeFile)) {
              this.cachedDbPath = cmakeFile;
              return cmakeFile;
            }
          }
        }
      } catch (err) {
        console.error(`Error querying CMake Tools API: ${err}`);
      }
    }

    // 2. Fallback to manual search
    let currentDir = path.dirname(activeFilePath);
    const root = path.parse(currentDir).root;

    while (currentDir !== root) {
      const possiblePaths = [
        path.join(currentDir, 'compile_commands.json'),
        path.join(currentDir, 'build', 'compile_commands.json')
      ];

      for (const p of possiblePaths) {
        if (fs.existsSync(p)) {
          this.cachedDbPath = p;
          return p;
        }
      }

      const parentDir = path.dirname(currentDir);
      if (parentDir === currentDir) {
        break;
      }
      currentDir = parentDir;
    }

    this.cachedDbPath = null;
    return null;
  }

  public dispose(): void {
    this.disposables.forEach(d => d.dispose());
    this.disposables = [];
    this._onDatabaseChanged.dispose();
  }
}
