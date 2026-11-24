import { execFile } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import cors from 'cors';
import express from 'express';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const WEB_ROOT = path.resolve(__dirname, '..');
const REPO_ROOT = path.resolve(WEB_ROOT, '..');
const DATA_PATH = path.join(WEB_ROOT, 'public', 'data', 'ou_3pt_data.json');
const DIST_DIR = path.join(WEB_ROOT, 'dist');

const app = express();
app.use(cors());
app.use(express.json());

function readDataset() {
  if (!fs.existsSync(DATA_PATH)) {
    throw new Error('Dataset not found. Run `python main.py analyze` from the project root.');
  }
  return JSON.parse(fs.readFileSync(DATA_PATH, 'utf-8'));
}

app.get('/api/data', (_req, res) => {
  try {
    res.json(readDataset());
  } catch (err) {
    res.status(500).json({ error: err instanceof Error ? err.message : 'Failed to load dataset' });
  }
});

app.post('/api/sync', (req, res) => {
  const season = typeof req.body?.season === 'string' && /^\d{4}-\d{2}$/.test(req.body.season)
    ? req.body.season
    : '2026-27';

  execFile(
    'python',
    ['main.py', 'run', '--seasons', season],
    { cwd: REPO_ROOT, timeout: 120_000 },
    (error, stdout, stderr) => {
      if (error) {
        res.status(500).json({
          synced: false,
          message: stderr?.trim() || error.message || 'Sync failed',
        });
        return;
      }
      try {
        const data = readDataset();
        res.json({
          synced: true,
          message: `Synced ${season} from goldengrizzlies.com (${data.totalGames} total games through ${data.asOfDate}).`,
          log: stdout.trim(),
          data,
        });
      } catch (readErr) {
        res.status(500).json({
          synced: false,
          message: readErr instanceof Error ? readErr.message : 'Synced, but failed to read updated data',
        });
      }
    },
  );
});

if (fs.existsSync(DIST_DIR)) {
  app.use(express.static(DIST_DIR));
  app.get('/{*splat}', (_req, res) => {
    res.sendFile(path.join(DIST_DIR, 'index.html'));
  });
}

const PORT = Number(process.env.PORT) || 3002;
app.listen(PORT, () => {
  console.log(`GrizzThree server running at http://localhost:${PORT}`);
});
