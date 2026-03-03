from .base import PipelineStep, StepIO
import os

class CompileCommandsLoader(PipelineStep):
    name = "00_load_compile_commands"

    def io(self, context):
        return StepIO(
            inputs=[self.config["compile_commands"]],
            outputs=[]
        )

    def run(self, context):
        path = self.config["compile_commands"]

        if not os.path.exists(path):
            raise FileNotFoundError(f"compile_commands.json not found: {path}")

        print(f"[compile_commands] Using existing file: {path}")