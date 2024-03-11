# HouseAlert

## What is HouseAlert ?

Our application is a Python-based web scraper that **monitors rental listings on real estate agency** websites in **Paris, France**. Users can set their preferred criteria, such as location, price range, number of bedrooms, and other amenities. The scraper runs periodically to check for new listings that match the user's criteria. When a new listing is found, the application sends an alert to the user via a Telegram bot.

The use of a Telegram bot for alerts ensures that users receive notifications in real time, even when they are not actively using the application.

Overall, our application is a convenient and effective way to stay up-to-date with the latest rental listings on real estate agency websites. It saves users time and effort by automating the search process and delivering relevant results directly to their Telegram inbox.

## Managed real estate agencies

* [In'li](https://www.inli.fr/)
* [Crédit Agricole Immobilier](https://www.ca-immobilier.fr/)
* [Cattalan Johnson](https://www.cattalanjohnson.com/fr/)
* [CDC Habitat](https://www.cdc-habitat.fr/)
* [Concordia](https://agenceconcordia.com/nos-appartements-a-la-location/)
* [GTF](https://www.gtf.fr/liste-des-biens-loueur)

## Features

* Customizable search criteria, including location, price range, number of bedrooms, and other amenities
* Periodic scraping (default : each 10 minutes) of real estate agency websites to check for new listings
* Real-time alerts via Telegram bot when new listings are found
* **(Coming...)** Easy-to-use interface for managing search criteria and alerts

## Requirements

* Python 3.x
* Telegram account and bot token
* Database (e.g. SQLite, PostgreSQL) for storing user preferences and search results

## Installation and setup

1. Clone the repository: `git clone https://github.com/yourusername/housealert.git`
2. Install requirements: `pip install -r requirements.txt`
3. Set up a Telegram bot and obtain a bot token
4. Configure the database connection settings
5. Run the application: `python main.py`

## TODO

- Add phone number to call in each agency
- Do only one connection to DB for all agencies
- _Specific cases by agency :_
  - **In'li**
    - Manage 502 Bad Gateway
  - **GTF**
    - Fix pictures
    - Manage address
    - Manage only Paris houses : add filter

## Contact

If you have any questions or feedback, please contact me on [LinkedIn](/https://www.linkedin.com/in/remibiou/).
