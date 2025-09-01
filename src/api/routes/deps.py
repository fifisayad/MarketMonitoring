from fastapi import Depends
from ...enums.exchange import Exchange
from ...service.manager import Manager
from ...service.info.info_factory import get_info


def create_manager() -> Manager:
    return Manager()


def create_info(exchange: Exchange):
    return get_info(exchange=exchange)
