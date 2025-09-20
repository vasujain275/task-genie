import { Schema, model } from "mongoose";

const taskSchema = new Schema({
  userId: { type: Schema.Types.ObjectId, ref: "User", required: true },
  title: { type: String, required: true },
  description: { type: String },
  datetime: { type: Date }, // main event time
  recurrence: {
    type: String,
    enum: ["none", "daily", "weekly", "monthly"],
    default: "none"
  },
  status: { type: String, enum: ["pending", "done"], default: "pending" },
  createdAt: { type: Date, default: Date.now },
});

export const Task = model("Task", taskSchema);
