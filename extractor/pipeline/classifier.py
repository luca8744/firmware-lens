from .base import PipelineStep, load_json, save_json, StepIO

class FunctionClassifier(PipelineStep):
    name = "03_classify_functions"

    def io(self, context):
        return StepIO(
            inputs=[self.config["functions_index"]],
            outputs=[self.config["function_categories"]]
        )

    def run(self, context):
        functions = load_json(self.config["functions_index"])
        out_path = self.config["function_categories"]

        def classify_function(name, file_path):
            p = (file_path or "").lower()

            if ("cmsis_os" in p or "rtos" in p or name.startswith("os")):
                return "rtos"

            if ("driver" in p or "hwlib" in p or "baselib" in p or name.startswith("Driver_") or name.startswith("BSP_")):
                return "driver"

            if ("utils" in p or "common" in p or "helper" in p or name.endswith("_Init")):
                return "utility"

            return "application"

        categories = {}
        for fn, info in functions.items():
            categories[fn] = classify_function(fn, info.get("file"))

        save_json(out_path, categories)
        context["function_categories"] = out_path
        self.log(f"Classified {len(categories)} functions")
