import { database } from "./config/database";
import buildServer from "./server";
import { port } from "./utils/constants";
import { logger } from "./utils/logger";

export const server = buildServer();

async function main() {
  try {
    // Connect to MongoDB before starting the server
    logger.info("Connecting to MongoDB...");
    await database.connect();

    // Start the server
    logger.info(`Starting server on port ${port}...`);
    await server.listen({
      port: port,
      host: "0.0.0.0",
    });

    logger.info(`🚀 Server is running on http://0.0.0.0:${port}`);
    logger.info(`📊 Health check available at http://0.0.0.0:${port}/v1/healthcheck`);

  } catch (error) {
    logger.error("Failed to start application:", error);
    process.exit(1);
  }
}

// Graceful shutdown handling
async function gracefulShutdown(signal: string) {
  logger.info(`Received ${signal}. Starting graceful shutdown...`);

  try {
    // Close server first
    await server.close();
    logger.info("Server closed successfully");

    // Then disconnect from database
    await database.disconnect();
    logger.info("Database disconnected successfully");

    logger.info("Graceful shutdown completed");
    process.exit(0);
  } catch (error) {
    logger.error("Error during graceful shutdown:", error);
    process.exit(1);
  }
}

// Handle process termination signals
for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => gracefulShutdown(signal));
}

// Handle uncaught exceptions and rejections
process.on("uncaughtException", (error) => {
  logger.error("Uncaught Exception:", error);
  gracefulShutdown("uncaughtException");
});

process.on("unhandledRejection", (reason, promise) => {
  logger.error("Unhandled Rejection at:", promise, "reason:", reason);
  gracefulShutdown("unhandledRejection");
});

main();
