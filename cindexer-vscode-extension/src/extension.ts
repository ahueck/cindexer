import * as vscode from 'vscode';
import * as path from 'path';
import { getBaseCommunicationDir, initializeBaseDir } from './ipc/directory';
import { StatePublisher } from './statePublisher';
import { RequestListener } from './requestListener';

let publisher: StatePublisher | undefined;
let listener: RequestListener | undefined;

export function activate(context: vscode.ExtensionContext) {
    const baseDir = getBaseCommunicationDir('cindexer');
    
    try {
        initializeBaseDir(baseDir);
        publisher = new StatePublisher(baseDir);
        listener = new RequestListener(publisher.sessionDir, publisher);
        
        // Initial publish
        publisher.publishState();

        // Subscribe to relevant events
        context.subscriptions.push(
            vscode.window.onDidChangeActiveTextEditor(() => publisher?.publishState()),
            vscode.window.onDidChangeWindowState(() => publisher?.publishState()),
            vscode.workspace.onDidSaveTextDocument(() => publisher?.publishState())
        );

        context.subscriptions.push({
            dispose: () => {
                listener?.dispose();
                publisher?.dispose();
            }
        });

    } catch (err) {
        vscode.window.showErrorMessage(`Failed to initialize CIndexer IPC: ${err}`);
    }
}

export function deactivate() {
    listener?.dispose();
    publisher?.dispose();
}
