import { Schema, model } from "mongoose";

const userSchema = new Schema({
  telegramId: { type: Number, required: true, unique: true },
  name: { type: String },
  geminiKey: { type: String },
  openAIKey: { type: String },
  defaultAI: { type: String, enum: ["gemini", "openai"], default: "gemini" },
  timezone: { type: String, default: "Asia/Kolkata" },
  createdAt: { type: Date, default: Date.now },
});

export const User = model("User", userSchema);
