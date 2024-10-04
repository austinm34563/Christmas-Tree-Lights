import logging

class Logger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance

    def _initialize_logger(self):
        # Set up the logger configuration
        self.logger = logging.getLogger("SingletonLogger")
        self.logger.setLevel(logging.DEBUG)

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
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def debug(self, tag, message):
        tagged_message = f"[{tag}] {message}"
        self.logger.debug(tagged_message)

    def info(self, tag, message):
        tagged_message = f"[{tag}] {message}"
        self.logger.info(tagged_message)

    def warning(self, tag, message):
        tagged_message = f"[{tag}] {message}"
        self.logger.warning(tagged_message)

    def error(self, tag, message):
        tagged_message = f"[{tag}] {message}"
        self.logger.error(tagged_message)

    def critical(self, tag, message):
        tagged_message = f"[{tag}] {message}"
        self.logger.critical(tagged_message)