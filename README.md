# Market Monitoring Service

## 🧭 Introduction

This service provides **real-time market data** for trading pairs from the **Hyperliquid exchange**.  
It is designed to be **lightweight**, **reliable**, and **modular**, enabling seamless integration with other systems through **Python shared memory**.

The system continuously monitors market updates at a **1-minute ("1m") interval**, ensuring stable and accurate statistics that can be accessed by connected processes.

---

## ⚙️ Service Design

The service is built with simplicity and reliability in mind, focusing on efficient configuration and stable data delivery.

### 1. Configuration-Based Initialization  
- The system is configured via a lightweight configuration file or environment variables.  
- No API gateway or dynamic subscriptions are required — configuration defines all monitored pairs and parameters.

### 2. Core Data Engine  
- Connects exclusively to the **Hyperliquid** exchange.  
- Collects live market data at a **1-minute interval**.  
- Uses asynchronous processing (`asyncio`) for efficient and consistent updates.  
- Maintains reliability through reconnection and validation mechanisms.

### 3. Shared Memory Integration  
- Publishes live market data and statistics into **Python Shared Memory** segments.  
- Other local services or analytics modules can directly read from shared memory for **fast, low-latency data access**.  
- Eliminates dependency on external message brokers (like Redis) while improving performance and stability.

---

## 🛠️ Tech Stack

| Component            | Technology / Tool             | Description                                                                 |
|----------------------|-------------------------------|-----------------------------------------------------------------------------|
| **Exchange**         | [Hyperliquid](https://hyperliquid.xyz/) | Supported exchange for real-time data collection                            |
| **Concurrency**      | `asyncio` / `anyio`           | High-performance asynchronous event loop for data processing                |
| **Data Sharing**     | Python Shared Memory (`multiprocessing.shared_memory`) | Fast and lightweight interprocess communication                             |
| **Language**         | Python 3.10+                  | Core implementation language                                                |
| **Other Tools**      | Docker, Pydantic              | Containerization, configuration validation, and deployment management       |

---
## 🚢 Live Commands
- for reading last candles of markets and its stats
```shell
python read.py

or

docker exec -it market-monitoring python read.py

```

- for reading based on market
```shell
python read.py --market btcusd_perp

or

docker exec -it market-monitoring python read.py --market btcusd_perp

```
- for reading based on stat
```shell
python read.py --stat ATR14

or

docker exec -it market-monitoring python read.py --stat RSI5

```
---
## 🧩 Key Features

- ✅ **Single Exchange Support** — Focused on **Hyperliquid** for optimized stability  
- 🕐 **Fixed Interval** — Data updates every **1 minute**  
- 💾 **Shared Memory Integration** — Zero-copy data sharing between local services  
- 🔄 **Reliable and Stable Updates** — Automatic reconnection and error handling  
- ⚙️ **Configuration-Based Setup** — No API or external trigger required  

---

## 📄 License

This project is licensed under the **MIT License**.  
See the [LICENSE](LICENSE) file for details.


