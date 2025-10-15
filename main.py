from fifi.helpers.get_logger import LoggerFactory

from src.engines.manager import Manager


LOGGER = LoggerFactory().get(__name__)


if __name__ == "__main__":
    manager = Manager()
    manager.start()
