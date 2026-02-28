import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

export function getBaseCommunicationDir(name: string): string {
  const info = os.userInfo();

  // On POSIX, we suffix with the UID to avoid cross-user collisions in /tmp.
  // On Windows, info.uid is often -1 or not applicable in the same way,
  // and the temp dir is already user-scoped.
  const suffix = info.uid >= 0 ? `-${info.uid}` : '';

  // Prioritize environment variables to match Python's tempfile.gettempdir()
  const tmpDir = process.env.TMPDIR || process.env.TEMP || process.env.TMP || os.tmpdir();

  return path.join(tmpDir, `${name}${suffix}`);
}

export function initializeBaseDir(baseDir: string): void {
  if (!fs.existsSync(baseDir)) {
    fs.mkdirSync(baseDir, { recursive: true, mode: 0o700 });
  } else {
    // Security check: ensure it's a directory and owned by us
    const stats = fs.lstatSync(baseDir);
    const info = os.userInfo();

    if (!stats.isDirectory() || stats.isSymbolicLink()) {
      throw new Error(`Invalid communication directory: ${baseDir} is not a directory`);
    }

    // On POSIX, check ownership
    if (info.uid >= 0 && stats.uid !== info.uid) {
      throw new Error(`Security error: ${baseDir} is owned by another user`);
    }

    // Ensure restrictive permissions (0700)
    fs.chmodSync(baseDir, 0o700);
  }

  const sessionsDir = path.join(baseDir, 'sessions');
  if (!fs.existsSync(sessionsDir)) {
    fs.mkdirSync(sessionsDir, { recursive: true, mode: 0o700 });
  }
}
