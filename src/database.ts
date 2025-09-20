// Database connection
export { DatabaseConnection, database } from "./config/database";

// Models
export { Reminder } from "./modules/reminder/reminder.model";
export { Task } from "./modules/task/task.model";
export { User } from "./modules/user/user.model";

// Types for better TypeScript support
export interface DatabaseStatus {
  connected: boolean;
  state: string;
}

export interface HealthCheckResponse {
  status: string;
  database: DatabaseStatus;
  timestamp: string;
}
