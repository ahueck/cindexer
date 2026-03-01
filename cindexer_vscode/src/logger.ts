import * as vscode from 'vscode';

export class Logger {
  private static channel: vscode.OutputChannel | undefined;

  public static init(): void {
    if (!this.channel) {
      this.channel = vscode.window.createOutputChannel('CIndexer IPC');
    }
  }

  public static info(message: string): void {
    this.log('INFO', message);
  }

  public static warn(message: string): void {
    this.log('WARN', message);
  }

  public static error(message: string): void {
    this.log('ERROR', message);
  }

  private static log(level: string, message: string): void {
    if (!this.channel) {
      this.init();
    }
    const timestamp = new Date().toISOString();
    this.channel?.appendLine(`[${timestamp}] [${level}] ${message}`);
  }

  public static dispose(): void {
    this.channel?.dispose();
    this.channel = undefined;
  }
}
