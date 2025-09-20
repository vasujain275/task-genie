const port: number = parseInt(process.env.PORT || "8069", 10);
const mongodbUri: string = process.env.MONGODB_URI || "mongodb://localhost:27017/taskgenie";
const nodeEnv: string = process.env.NODE_ENV || "development";

export { mongodbUri, nodeEnv, port };

