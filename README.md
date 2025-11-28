# 🧠 **FedEdge v0.1.0 (Beta)**
### *Decentralized AI Copilot for Crypto, DeFi, and Beyond*

**FedEdge** is an **AI-powered cryptocurrency and DeFi copilot** that combines **real-time market intelligence**, **autonomous trading agents**, and **federated learning on edge devices** — bringing privacy-preserving intelligence to every user.

Built for traders, researchers, and AI enthusiasts, FedEdge offers:

- ⚙️ **Autonomous trading orchestration** — from signal detection to execution and PnL tracking.  
- 📊 **Real-time analytics & portfolio insights** powered by local AI reasoning.  
- 🤖 **Multi-agent architecture** *(Planner, Executor, Critic)* for adaptive decision-making.  
- 🔗 **Federated Learning on Edge Devices** — each device contributes to global intelligence while preserving privacy.  
- 🧩 **DeFi & Smart Contract analysis** *(in progress)* — future AI tools to interpret and reason about blockchain data.  
- 💡 **Local-first design** — all intelligence runs on your hardware *(Jetson, Raspberry Pi, PC…)* for maximum sovereignty.

> **FedEdge** is building the first open platform merging **AI trading agents**, **federated learning**, and **blockchain governance**, enabling a new era of **shared intelligence — privately trained, collectively improved.**

---

## 🚀 Quick Start



```
curl -fsSL https://fededge.net/deploy.sh | bash
``` 

### 🧩 Run with Docker (you can install docker simply with :  curl -fsSL https://get.docker.com | sudo sh)
FedEdge is available as a ready-to-run Docker image.  
Pull and start the **beta** version in one command:

```bash
docker run -d \
  --name fededge \
  -p 8000:8000 \
  -p 9001:9001 \
  -p 9002:9002 \
  -v $(pwd)/data:/app/data \
  imedmag2020/fededge:v0.1.0
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

---

### 💻 Run from Source (Developer Mode)

```bash
# 1. Clone the repository
git clone https://github.com/Imag2020/fededge
cd fededge

# 2. (Optional) Create a Python virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4.0  Download local Model in ./models

mkdir -p models && \
wget -O models/gemma-3-4b-it-Q4_K_M.gguf \
  https://huggingface.co/unsloth/gemma-3-4b-it-GGUF/resolve/main/gemma-3-4b-it-Q4_K_M.gguf

# 4.1 Start the local LLM server (for chat & embeddings) 
./start_llamacpp.sh

4.3 Please note that you can use external LLM/embeddings models via external API  (ollama, OpenAi .. etc) available in Settings menu

# 5. Launch the backend
python run_server.py


```

---

## 🧠 Key Features

| Feature | Description |
|:--|:--|
| ⚙️ **Autonomous Trading** | Multi-agent orchestration with signal detection, strategy evaluation, and OCO trade execution. |
| 📊 **Analytics Dashboard** | Real-time monitoring of trades, PnL, and win-rate by hour/strategy. |
| 🤖 **AI Copilot** | Local reasoning agents for market insights and natural language chat. |
| 🔗 **Federated Learning (Edge)** | Each node trains locally and contributes to collective intelligence. |
| 🧩 **DeFi / Smart Contracts** | *Under development — contributors welcome to collaborate!* |
| 💡 **Local & Private** | No centralized API calls — all runs locally for full sovereignty. |

---

## 🌐 Vision

FedEdge pioneers **on-device federated learning** for decentralized AI intelligence.  
Our mission: **Empower every node with AI — privately trained, collectively improved.**

> 🪙 *"Decentralizing Alpha. On Your Device."*

---

## 🤝 Call for Contributors & Beta Testers

FedEdge is in **active beta** — we're looking for **contributors, testers, and early adopters**.  
If you’re passionate about **AI, DeFi, trading, blockchain, or edge intelligence**, join us!

- 🧪 Test the beta version locally or on your Jetson/Raspberry Pi  
- 🧩 Contribute code or models (LLM, agents, data pipelines, blockchain logic)  
- 💬 Join the discussion on our upcoming community Discord

---

## 📄 License
Business Source License 1.1 © 2025 FedEdge Project

See [LICENSE](./LICENSE) file for details.

---

## 🧭 Links
- 🌍 [Official Website](https://fededge.net)
- 🐙 [GitHub Repository](https://github.com/fededge/fededge)
- 🐳 [Docker Hub Image](https://hub.docker.com/r/fededge/fededge)
- 💬 [Community (coming soon)](https://discord.gg/)
