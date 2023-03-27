# CTFTime does not expose an API to get events per team, so we can webscrape

from bs4 import BeautifulSoup
import requests
import seaborn
import aiohttp
import asyncio
from datetime import datetime, date
import pandas as pd
import matplotlib.pyplot as plt

async def get(session: aiohttp.ClientSession, url: str):
  async with session.get(url) as response:
    return await response.json()

async def get_event_info(event_ids: list):
  tasks = []
  async with aiohttp.ClientSession() as session:
    async with asyncio.TaskGroup() as group:
      for id in event_ids:
        tasks.append(group.create_task(get(session, f'https://ctftime.org/api/v1/events/{id}/')))
    result_arr = [task.result() for task in tasks]
    return {f'{result["id"]}': result for result in result_arr}

def parse_pane(html):
  rows = html.find('table').find_all("tr")[1:]
  results = []
  for row in rows:
    [_, place, link, _, rating_points] = list(row.find_all("td"))
    url = link.find("a").get("href")
    name = link.find("a").text
    results.append({
      "place": int(place.text),
      "url": url,
      "name": name,
      "rating_points": float(rating_points.text)
    })
  return results

def get_results(team_id):
  page = requests.get(f"https://ctftime.org/team/{team_id}", headers={
    "User-Agent": "https://github.com/reteps/ctftime-team-graphs"
  })
  soup = BeautifulSoup(page.content, 'html.parser')
  tabs = soup.find("div", class_="tab-content").find_all("div", class_="tab-pane")
  return {tab.get("id").replace("rating_",""): parse_pane(tab) for tab in tabs}


if __name__ == "__main__":
  results = get_results(27763)
  for year, events in results.items():
    event_ids = [event["url"].split("/")[-1] for event in events]
    event_info = asyncio.run(get_event_info(event_ids))
    for event in events:
      event["start"] = datetime.fromisoformat(event_info[event["url"].split("/")[-1]]["start"])
    events.sort(key=lambda event: event["start"])
  
  results_flat = []
  for year, events in results.items():
    for event in events:
      results_flat.append({
        "year": year,
        "start": event["start"],
        "place": event["place"]
      })
  results_df = pd.DataFrame(results_flat)
  results_df['date_ordinal'] = pd.to_datetime(results_df['start']).apply(lambda date: date.toordinal())

  # color per year, y axis rating points, x axis time
  plt.yscale('log')
  ax = seaborn.regplot(x ="date_ordinal", y="place", data=results_df, scatter=True)
  ax.set_xlim(results_df['date_ordinal'].min() - 1, results_df['date_ordinal'].max() + 1)
  ax.set_ylim(0, results_df['place'].max() + 1)
  ax.set_xlabel('date')
  new_labels = [date.fromordinal(int(item)) for item in ax.get_xticks()]
  ax.set_xticklabels(new_labels)
  plt.show()