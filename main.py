from modules.interface import run_cli
import logging

if __name__ == "__main__":
    # 配置根日志级别，可根据需要改为 DEBUG
    logging.basicConfig(level=logging.INFO)
    run_cli()
