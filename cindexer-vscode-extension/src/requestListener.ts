import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import { StatePublisher } from './statePublisher';

export class RequestListener {
    private readonly requestPath: string;
    private watcher: fs.FSWatcher | undefined;

    constructor(
        private readonly sessionDir: string,
        private readonly publisher: StatePublisher
    ) {
        this.requestPath = path.join(this.sessionDir, 'python_request.json');
        this.startWatching();
    }

    private startWatching(): void {
        if (!fs.existsSync(this.sessionDir)) { return; }

        // We watch the directory for the request file
        this.watcher = fs.watch(this.sessionDir, (event, filename) => {
            if (filename === 'python_request.json' && fs.existsSync(this.requestPath)) {
                this.handleRequest();
            }
        });
    }

    private handleRequest(): void {
        try {
            const content = fs.readFileSync(this.requestPath, 'utf-8');
            const request = JSON.parse(content);
            
            console.log(`Received CIndexer request: ${request.type} (${request.requestId})`);

            switch (request.type) {
                case 'ping':
                    // Just refresh state as acknowledgement
                    this.publisher.publishState();
                    break;
                case 'get_state':
                    this.publisher.publishState();
                    break;
                case 'reveal_file':
                    if (request.data?.path) {
                        const uri = vscode.Uri.file(request.data.path);
                        vscode.window.showTextDocument(uri);
                    }
                    break;
                default:
                    console.warn(`Unknown request type: ${request.type}`);
            }

            // Cleanup request file after processing (optional, but good for one-shots)
            // In our protocol, VS Code reacts but doesn't necessarily write a "response" file 
            // yet unless we want full bi-di. The plan says "Implicitly or explicitly".
            // For now, we react by updating the state file.
            
        } catch (err) {
            console.error(`Error handling request: ${err}`);
        }
    }

    public dispose(): void {
        this.watcher?.close();
    }
}
