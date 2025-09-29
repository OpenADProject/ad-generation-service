import os
import json
import config
from pipeline import ImageGenerationPipeline
from logger import setup_logger, PerformanceMonitor, GPTLogAnalyzer


def get_next_run_dir(base_dir="outputs"):
    os.makedirs(base_dir, exist_ok=True)
    existing = [d for d in os.listdir(base_dir) if d.isdigit()]
    run_id = max(map(int, existing), default=0) + 1
    run_dir = os.path.join(base_dir, str(run_id))
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def run_pipeline(input_data: dict) -> dict:
    logger = setup_logger()
    performance_monitor = PerformanceMonitor(logger)
    gpt_analyzer = GPTLogAnalyzer(logger)
    result = None
    try:
        performance_monitor.start()
        pipeline = ImageGenerationPipeline(config=config, logger=logger, output_dir="outputs")
        result = pipeline.run(input_data)
        if result and result.get("status") == "success":
            logger.info("Pipeline completed successfully.")
    except Exception as e:
        logger.error("Unhandled exception", exc_info=True)
        gpt_analyzer.analyze_error(e, {"prompt": input_data.get("prompt"), "params": input_data.get("params")})
        result = {"status": "error", "message": str(e)}
    finally:
        performance_monitor.end()
    return result


def main():
    logger = setup_logger()

    with open("payload.json", "r", encoding="utf-8") as f:
        user_input = json.load(f)

    run_output_dir = get_next_run_dir()
    performance_monitor = PerformanceMonitor(logger)
    gpt_analyzer = GPTLogAnalyzer(logger)
    result = None

    try:
        performance_monitor.start()
        pipeline = ImageGenerationPipeline(config=config, logger=logger, output_dir=run_output_dir)
        result = pipeline.run(user_input)
        if result and result.get("status") == "success":
            logger.info("Pipeline completed successfully.")
    except Exception as e:
        logger.error("Unhandled exception", exc_info=True)
        gpt_analyzer.analyze_error(e, {"prompt": user_input.get("prompt"), "params": user_input.get("params")})
        result = {"status": "error", "message": str(e)}
    finally:
        performance_monitor.end()
        print("="*50)
        print("PIPELINE EXECUTION FINISHED")
        print("="*50)
        if result and result.get("status") == "success":
            print("성공")
        else:
            print(f"에러 : {result.get('message') if result else 'Unknown'}")
        print("="*50)


if __name__ == "__main__":
    main()