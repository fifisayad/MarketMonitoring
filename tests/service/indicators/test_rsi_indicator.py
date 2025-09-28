import pytest
import numpy as np
import time

from fakeredis.aioredis import FakeRedis
from unittest.mock import AsyncMock
from aredis_om.model.model import NotFoundError
from fifi.enums import Exchange, Market
from fifi import LoggerFactory
from src.service.indicators.rsi.hyperliquid_rsi_indicator import (
    HyperLiquidRSIIndicator,
    _rsi_numba,
)
from src.models.rsi_model import RSIModel

LOGGER = LoggerFactory.get(__name__)


@pytest.mark.asyncio
async def test_rsi_indicator_e2e(monkeypatch):
    # Fake Redis client
    fake_redis = FakeRedis()
    monkeypatch.setattr(
        "fifi.redis.redis_base_model.RedisClient.create",
        AsyncMock(return_value=AsyncMock(redis=fake_redis)),
    )

    # Create indicator
    indicator = HyperLiquidRSIIndicator(
        exchange=Exchange.HYPERLIQUID, market=Market.BTCUSD_PERP
    )

    # Fake snapshot
    monkeypatch.setattr(
        "src.service.indicators.rsi.hyperliquid_rsi_indicator.HyperliquidInfo.candle_snapshot",
        lambda self, market, timeframe="1m", period=500: [
            {"c": "100", "t": 1},
            {"c": "105", "t": 2},
            {"c": "110", "t": 3},
        ],
    )

    # Fake RedisSubscriber messages
    indicator.monitor = AsyncMock()
    indicator.monitor.get_messages = AsyncMock(
        return_value=[
            {"data": {"i": "1m", "c": "115", "t": "4"}},
        ]
    )

    # Bootstrap + subscribe
    await indicator.bootstrap_buffer("1m")
    indicator.subscribed_periods["1m"] = {14}

    LOGGER.info("Running one RSI update cycle...")

    # Simulate execution loop (one step)
    msgs = await indicator.monitor.get_messages()
    for msg in msgs:
        timeframe = msg["data"]["i"]
        close = float(msg["data"]["c"])
        timestamp = float(msg["data"]["t"])
        buffer = indicator.close_prices[timeframe]

        # Shift buffer to include confirmed candle
        buffer = np.roll(buffer, -1)
        buffer[-1] = close
        indicator.close_prices[timeframe] = buffer
        indicator.current_candle[timeframe] = timestamp

        # Compute RSI and store
        rsi_val = _rsi_numba(buffer, period=14)
        LOGGER.info(f"Computed RSI: {rsi_val}")

        pk = f"{indicator.exchange}_{indicator.market}_{timeframe}_14"
        try:
            rsi_model = await RSIModel.get_by_id(pk)
        except NotFoundError:
            rsi_model = await RSIModel.create(
                pk=pk,
                exchange=indicator.exchange,
                market=indicator.market,
                timeframe=timeframe,
                period=14,
                rsi=rsi_val,
                time=time.time(),
            )
            await rsi_model.save()
        else:
            await rsi_model.update(rsi=rsi_val, time=time.time())

    stored = await RSIModel.get_by_id(pk)
    LOGGER.info(f"Stored RSI in Redis: {stored.rsi}")
    assert stored.rsi is not None
    assert isinstance(stored.rsi, float)
