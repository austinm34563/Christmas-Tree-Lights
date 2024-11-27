import logging

class Logger:
    # Static logger initialization
    _logger = logging.getLogger("StaticLogger")
    _logger.setLevel(logging.DEBUG)
    _is_configured = False

    @staticmethod
    def _configure_logger():
        if not Logger._is_configured:
            # Create a file handler to write logs to a file
            file_handler = logging.FileHandler("output/output.log")
            file_handler.setLevel(logging.DEBUG)

            # Create a console handler for output to the terminal
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)

            # Create a formatter and set it for both handlers
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            # Add the handlers to the logger
            Logger._logger.addHandler(file_handler)
            Logger._logger.addHandler(console_handler)

            Logger._is_configured = True

    @staticmethod
    def debug(tag, message):
        Logger._configure_logger()
        tagged_message = f"[{tag}] {message}"
        Logger._logger.debug(tagged_message)

    @staticmethod
    def info(tag, message):
        Logger._configure_logger()
        tagged_message = f"[{tag}] {message}"
        Logger._logger.info(tagged_message)

    @staticmethod
    def warning(tag, message):
        Logger._configure_logger()
        tagged_message = f"[{tag}] {message}"
        Logger._logger.warning(tagged_message)

    @staticmethod
    def error(tag, message):
        Logger._configure_logger()
        tagged_message = f"[{tag}] {message}"
        Logger._logger.error(tagged_message)

    @staticmethod
    def critical(tag, message):
        Logger._configure_logger()
        tagged_message = f"[{tag}] {message}"
        Logger._logger.critical(tagged_message)
