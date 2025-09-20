import { nodeEnv } from "../utils/constants";

interface EnvConfig {
  port: number;
  mongodbUri: string;
  nodeEnv: string;
  isDevelopment: boolean;
  isProduction: boolean;
  isTest: boolean;
}

function validateEnvironment(): void {
  const requiredEnvVars = ["MONGODB_URI"];

  const missingVars = requiredEnvVars.filter(
    (varName) => !process.env[varName]
  );

  if (missingVars.length > 0) {
    throw new Error(
      `Missing required environment variables: ${missingVars.join(", ")}`
    );
  }
}

export function getConfig(): EnvConfig {
  // Only validate in production
  if (nodeEnv === "production") {
    validateEnvironment();
  }

  return {
    port: parseInt(process.env.PORT || "8069", 10),
    mongodbUri: process.env.MONGODB_URI || "mongodb://localhost:27017/taskgenie",
    nodeEnv,
    isDevelopment: nodeEnv === "development",
    isProduction: nodeEnv === "production",
    isTest: nodeEnv === "test",
  };
}

export const config = getConfig();
