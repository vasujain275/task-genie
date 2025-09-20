import { Schema, model } from "mongoose";

const reminderSchema = new Schema({
  taskId: { type: Schema.Types.ObjectId, ref: "Task", required: true },
  userId: { type: Schema.Types.ObjectId, ref: "User", required: true },
  remindAt: { type: Date, required: true }, // exact time to notify
  sent: { type: Boolean, default: false },  // has reminder been sent
  createdAt: { type: Date, default: Date.now },
});

export const Reminder = model("Reminder", reminderSchema);
