import * as vscode from 'vscode';

import { CompilationDatabaseProvider } from './compilationDatabaseProvider';
import { getBaseCommunicationDir, initializeBaseDir } from './ipc/directory';
import { RequestListener } from './requestListener';
import { StatePublisher } from './statePublisher';

let publisher: StatePublisher | undefined;
let listener: RequestListener | undefined;
let dbProvider: CompilationDatabaseProvider | undefined;

export function activate(context: vscode.ExtensionContext) {
  const baseDir = getBaseCommunicationDir('cindexer');

  try {
    initializeBaseDir(baseDir);
    dbProvider = new CompilationDatabaseProvider();
    publisher = new StatePublisher(baseDir, dbProvider);
    listener = new RequestListener(publisher.sessionDir, publisher);

    // Initial publish
    publisher.publishState().catch((err) => console.error(`Error in initial publishState: ${err}`));

    // Subscribe to relevant events
    context.subscriptions.push(
      dbProvider,
      dbProvider.onDatabaseChanged(() =>
        publisher?.publishState().catch((err) => console.error(`Error onDatabaseChanged: ${err}`)),
      ),
      vscode.window.onDidChangeActiveTextEditor(() =>
        publisher?.publishState().catch((err) => console.error(`Error onDidChangeActiveTextEditor: ${err}`)),
      ),
      vscode.window.onDidChangeWindowState(() =>
        publisher?.publishState().catch((err) => console.error(`Error onDidChangeWindowState: ${err}`)),
      ),
      // vscode.workspace.onDidSaveTextDocument(() =>
      // publisher?.publishState().catch(err => console.error(`Error
      // onDidSaveTextDocument: ${err}`)))
    );

    context.subscriptions.push({
      dispose: () => {
        listener?.dispose();
        publisher?.dispose();
        dbProvider?.dispose();
      },
    });
  } catch (err) {
    vscode.window.showErrorMessage(`Failed to initialize CIndexer IPC: ${err}`);
  }
}

export function deactivate() {
  listener?.dispose();
  publisher?.dispose();
  dbProvider?.dispose();
}
