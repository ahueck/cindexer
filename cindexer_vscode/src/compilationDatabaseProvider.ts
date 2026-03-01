import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import { CMakeToolsApi, getCMakeToolsApi, Version } from 'vscode-cmake-tools';

import { Logger } from './logger';

export class CompilationDatabaseProvider implements vscode.Disposable {
  private cmakeApi: CMakeToolsApi | undefined;
  private cachedDbPath: string | null = null;
  private lastScannedPath: string | null = null;
  private disposables: vscode.Disposable[] = [];

  private readonly _onDatabaseChanged = new vscode.EventEmitter<string | null>();
  public readonly onDatabaseChanged = this._onDatabaseChanged.event;

  public async getCompilationDatabasePath(activeFilePath?: string): Promise<string | null> {
    Logger.info(`getCompilationDatabasePath called for: ${activeFilePath || 'none'}`);
    if (activeFilePath && (!this.cachedDbPath || this.shouldRescan(activeFilePath))) {
      await this.updateCompilationDatabase(activeFilePath);
    }
    return this.cachedDbPath;
  }

  private shouldRescan(activeFilePath: string): boolean {
    if (!this.lastScannedPath) {
      return true;
    }
    const should = path.dirname(activeFilePath) !== path.dirname(this.lastScannedPath);
    if (should) {
      Logger.info(
        `Rescan triggered: directory changed from ${path.dirname(
          this.lastScannedPath,
        )} to ${path.dirname(activeFilePath)}`,
      );
    }
    return should;
  }

  private async getCMakeApi(): Promise<CMakeToolsApi | undefined> {
    if (!this.cmakeApi) {
      this.cmakeApi = await getCMakeToolsApi(Version.latest);
      if (this.cmakeApi) {
        Logger.info('Successfully obtained CMake Tools API.');
        this.disposables.push(this.cmakeApi.onActiveProjectChanged(() => this.updateAndNotify()));
        this.disposables.push(this.cmakeApi.onBuildTargetChanged(() => this.updateAndNotify()));
        this.disposables.push(this.cmakeApi.onLaunchTargetChanged(() => this.updateAndNotify()));
      } else {
        Logger.warn('CMake Tools API not available.');
      }
    }
    return this.cmakeApi;
  }

  private async updateAndNotify(): Promise<void> {
    const activeEditor = vscode.window.activeTextEditor;
    const newPath = await this.updateCompilationDatabase(activeEditor?.document.uri.fsPath);
    this._onDatabaseChanged.fire(newPath);
  }

  public async updateCompilationDatabase(activeFilePath?: string): Promise<string | null> {
    if (!activeFilePath) {
      return this.cachedDbPath;
    }

    Logger.info(`Updating compilation database for: ${activeFilePath}`);
    this.lastScannedPath = activeFilePath;

    this.cachedDbPath =
      (await this.tryFindViaCMake(activeFilePath)) ?? (await this.tryFindViaManualSearch(activeFilePath));

    if (!this.cachedDbPath) {
      Logger.warn('No compile_commands.json found.');
    }

    return this.cachedDbPath;
  }

  private async tryFindViaCMake(activeFilePath: string): Promise<string | null> {
    const api = await this.getCMakeApi();
    if (!api) {
      return null;
    }

    try {
      const fileUri = vscode.Uri.file(activeFilePath);
      const folder = vscode.workspace.getWorkspaceFolder(fileUri);
      if (!folder) {
        Logger.warn(`No workspace folder found for: ${activeFilePath}`);
        return null;
      }

      const cmakeProject = await api.getProject(folder.uri);
      const buildDir = await cmakeProject?.getBuildDirectory();

      if (!buildDir) {
        Logger.warn(`No CMake project or build directory found for workspace folder: ${folder.uri.fsPath}`);
        return null;
      }
      const cmakeFile = path.join(buildDir, 'compile_commands.json');
      if (fs.existsSync(cmakeFile)) {
        return cmakeFile;
      }
      Logger.warn(`CMake build directory exists but no compile_commands.json found at: ${cmakeFile}`);
    } catch (err) {
      Logger.error(`Error querying CMake Tools API: ${err}`);
    }
    return null;
  }

  private async tryFindViaManualSearch(activeFilePath: string): Promise<string | null> {
    Logger.info('Falling back to manual search for compile_commands.json...');
    let currentDir = path.dirname(activeFilePath);
    const root = path.parse(currentDir).root;

    while (currentDir !== root) {
      const possiblePaths = [
        path.join(currentDir, 'compile_commands.json'),
        path.join(currentDir, 'build', 'compile_commands.json'),
      ];

      for (const p of possiblePaths) {
        if (fs.existsSync(p)) {
          Logger.info(`Found compile_commands.json via manual search: ${p}`);
          return p;
        }
      }

      const parentDir = path.dirname(currentDir);
      if (parentDir === currentDir) {
        break;
      }
      currentDir = parentDir;
    }
    return null;
  }

  public dispose(): void {
    this.disposables.forEach((d) => d.dispose());
    this.disposables = [];
    this._onDatabaseChanged.dispose();
  }
}
