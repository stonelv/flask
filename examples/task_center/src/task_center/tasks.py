import random
import time

from .executor import TaskContext


def register_handlers(executor):
    @executor.register("long_running_task")
    def long_running_task(ctx: TaskContext):
        duration = ctx.payload.get("duration", random.randint(10, 30))
        stages = [
            (10, "Initializing..."),
            (30, "Processing data..."),
            (50, "Executing main logic..."),
            (70, "Validating results..."),
            (90, "Finalizing..."),
            (100, "Complete"),
        ]

        ctx.log(f"Starting long_running_task, expected duration: {duration}s")
        interval = duration / len(stages)

        for target_progress, stage_name in stages:
            if ctx.check_cancel():
                ctx.log("Task cancelled by user request")
                raise InterruptedError("Task was cancelled")

            ctx.update_progress(target_progress, stage_name)
            ctx.log(f"Stage: {stage_name}")
            time.sleep(interval)

        return {"duration": duration, "message": "Task completed successfully"}

    @executor.register("quick_task")
    def quick_task(ctx: TaskContext):
        ctx.update_progress(0, "Starting")
        time.sleep(0.5)
        ctx.update_progress(50, "Processing")
        time.sleep(0.5)
        ctx.update_progress(100, "Done")
        return {"result": "quick_result", "input": ctx.payload}
