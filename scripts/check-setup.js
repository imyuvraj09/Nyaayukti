// Local wiring checks only. Never print configuration values containing secrets.
const fs = require('node:fs');
const path = require('node:path');
const net = require('node:net');
const { parseEnv } = require('node:util');
const root = path.resolve(__dirname, '..');
function readEnv(service) {
  const file = path.join(root, service, '.env');
  if (!fs.existsSync(file))
    throw new Error(`Missing ${service}/.env; run python scripts/configure_local.py.`);
  return parseEnv(fs.readFileSync(file, 'utf8'));
}
function port(value, fallback) {
  const n = Number(value || fallback);
  if (!Number.isInteger(n) || n < 1024 || n > 65535)
    throw new Error('Local service ports must be integers from 1024 to 65535.');
  return n;
}
function configuration() {
  const backend = readEnv('backend'),
    rag = readEnv('rag-service'),
    frontend = readEnv('frontend');
  const ports = {
    frontend: port(frontend.FRONTEND_PORT, 5173),
    backend: port(backend.PORT, 3000),
    rag: port(rag.PORT, 8000),
  };
  if (new Set(Object.values(ports)).size !== 3)
    throw new Error('Each service needs a different port.');
  if (!backend.RAG_SERVICE_TOKEN || backend.RAG_SERVICE_TOKEN !== rag.RAG_SERVICE_TOKEN)
    throw new Error('Backend and RAG service tokens are missing or do not match.');
  if (backend.RAG_SERVICE_URL !== `http://127.0.0.1:${ports.rag}`)
    throw new Error('Backend RAG_SERVICE_URL does not match the configured local RAG port.');
  if (frontend.BACKEND_PROXY_URL !== `http://127.0.0.1:${ports.backend}`)
    throw new Error('Frontend BACKEND_PROXY_URL does not match the configured backend port.');
  if (backend.FRONTEND_URL !== `http://localhost:${ports.frontend}`)
    throw new Error('Backend FRONTEND_URL does not match the frontend port.');
  if (frontend.VITE_API_BASE_URL && frontend.VITE_API_BASE_URL !== '/api')
    throw new Error('Use VITE_API_BASE_URL=/api for the local authenticated proxy.');
  return { ports, root };
}
async function ensurePortsFree(ports) {
  for (const [service, value] of Object.entries(ports)) {
    await new Promise((resolve, reject) => {
      const server = net.createServer();
      server.once('error', () =>
        reject(
          new Error(
            `${service} port ${value} is unavailable. Stop the old project or choose a consistent new port set. No process was terminated.`,
          ),
        ),
      );
      server.listen(value, () => server.close(resolve));
    });
  }
}
async function check() {
  const config = configuration();
  await ensurePortsFree(config.ports);
  console.log(
    `Project: ${root}\nPipeline: issue-evidence-v4.0\nFrontend: http://localhost:${config.ports.frontend}\nBackend: ${config.ports.backend}; RAG: ${config.ports.rag}\nLocal configuration agrees; ports are free. This is not a model or database readiness test.`,
  );
  return config;
}
if (require.main === module)
  check().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
module.exports = { check, configuration, readEnv };
