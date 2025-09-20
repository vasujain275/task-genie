import Fastify from "fastify";
import { database } from "./config/database";
import { loggerStream } from "./utils/logger";

function buildServer() {
  const server = Fastify({
    logger: {
      stream: loggerStream,
    },
  });

  // Health check endpoint with database status
  server.get("/v1/healthcheck", async () => {
    const dbStatus = database.isHealthy();
    const dbState = database.getConnectionState();

    return {
      status: "OK",
      database: {
        connected: dbStatus,
        state: dbState,
      },
      timestamp: new Date().toISOString(),
    };
  });

  return server;
}

export default buildServer;
