# 🏠 House-Alert

A Python automation script that monitors Parisian real estate agency websites for new rental listings and sends **Telegram notifications** when a listing matches your price and size criteria.

<p align="center">
  <img src="https://i.ibb.co/zhjQFPc/Capture-d-e-cran-2024-03-11-a-19-33-25.png" alt="Screenshot from House-Alert Telegram bot" style="width:20vw;height:auto;">
  <br>
  <em>Example notification received on Telegram</em>
</p>

---

## How it works

1. The script scrapes the listing page of each configured agency
2. For every listing found, it checks a **PostgreSQL database** to see if a notification has already been sent
3. If the listing is new **and** matches the price/size criteria defined in `utils/utils.py`, it sends a **Telegram message** (with images when available)
4. The listing is then marked as notified in the database to avoid duplicate alerts
5. The whole process runs **every minute** via GitHub Actions

---

## Monitored agencies

| Agency | Website |
|---|---|
| In'li | [inli.fr](https://www.inli.fr/) |
| Crédit Agricole Immobilier | [ca-immobilier.fr](https://www.ca-immobilier.fr/) |
| Cattalan Johnson | [cattalanjohnson.com](https://www.cattalanjohnson.com/fr/) |
| CDC Habitat | [cdc-habitat.fr](https://www.cdc-habitat.fr/) |
| Concordia | [agenceconcordia.com](https://agenceconcordia.com/nos-appartements-a-la-location/) |
| GTF | [gtf.fr](https://www.gtf.fr/liste-des-biens-loueur) |
| Brews | [brews.fr](https://www.brews.fr/) |
| Agence Dupleix | [dupleix.com](https://www.dupleix.com) |

---

## Customizing search criteria

Edit `TARGET_HOUSES` in `utils/utils.py` to set your price/size brackets:

```python
TARGET_HOUSES = [
    {"price": 900.0,  "sizeMin": 25.0},  # ≥25 m² for ≤900 €/month
    {"price": 1100.0, "sizeMin": 30.0},
    {"price": 1200.0, "sizeMin": 35.0},
    {"price": 1300.0, "sizeMin": 40.0},
    {"price": 1500.0, "sizeMin": 50.0},  # ≥50 m² for ≤1500 €/month
]
```

A listing matches if it satisfies **at least one** bracket (size ≥ minimum AND price ≤ maximum).

---

## Running locally

### Prerequisites

- Python 3.9+
- A PostgreSQL database with an `alert` table (see schema below)
- A Telegram bot token and a chat ID

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/House-Alert.git
cd House-Alert

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your values

# 5. Run
python main.py
```

### Database schema

```sql
CREATE TABLE public.alert (
    unique_id     TEXT        NOT NULL,
    provider      TEXT        NOT NULL,
    creation_date TIMESTAMP   NOT NULL,
    PRIMARY KEY (unique_id, provider)
);
```

---

## Environment variables

| Variable | Description |
|---|---|
| `DB_URI` | PostgreSQL connection URI (e.g. `postgresql://user:pass@host:port/db`) |
| `TELEGRAM_KEY` | Telegram bot token (from [@BotFather](https://t.me/BotFather)) |
| `CHAT_ID` | Target Telegram chat ID (user or group) |

Create a `.env` file at the project root for local development:

```dotenv
DB_URI=postgresql://user:password@host:5432/dbname
TELEGRAM_KEY=your_bot_token
CHAT_ID=your_chat_id
```

> **Never commit `.env` to Git.** It is already excluded by `.gitignore`.

---

## GitHub Actions

The workflow file is at `.github/workflows/main.yml`. It:
- Runs **every minute** on a cron schedule
- Uses **Python 3.9** on `ubuntu-latest`
- Reads `DB_URI`, `TELEGRAM_KEY`, and `CHAT_ID` from **GitHub Secrets** (Settings → Secrets and variables → Actions)
- Installs dependencies from `requirements.txt` and executes `python main.py`

To set up GitHub Secrets:  
**Repository → Settings → Secrets and variables → Actions → New repository secret**

---

## Project structure

```
House-Alert/
├── .github/
│   └── workflows/
│       └── main.yml          # GitHub Actions workflow
├── agencies/
│   ├── brews.py              # Brews scraper
│   ├── ca.py                 # Crédit Agricole Immobilier scraper
│   ├── cattalanjohnson.py    # Cattalan Johnson scraper
│   ├── cdc.py                # CDC Habitat scraper
│   ├── concordia.py          # Agence Concordia scraper
│   ├── dupleix.py            # Agence Dupleix scraper
│   ├── gtf.py                # GTF scraper
│   └── inli.py               # In'li scraper
├── utils/
│   ├── constants.py          # Shared message templates
│   ├── db_connexion.py       # PostgreSQL connection
│   ├── notify.py             # Telegram notification logic
│   └── utils.py              # Logging + price/size filter
├── main.py                   # Entry point
├── requirements.txt          # Python dependencies
└── .env                      # Local environment variables (not committed)
```

---

## License

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Licensed under the **Apache 2.0** License — see the [LICENSE](LICENSE) file for details.

## Contact

Questions or feedback? Reach me on [LinkedIn](https://www.linkedin.com/in/remibiou/).
