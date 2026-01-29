import requests
import json

from bs4 import BeautifulSoup

from pprint import pprint

def fetch_dneg_jobs():
    print("--- Fetching DNEG Jobs ---")
    url = "https://jobs.jobvite.com/double-negative-visual-effects"
    headers = {"User-Agent": "Mozilla/5.0"}

    jobs = []
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        job_rows = soup.find_all("li", class_="mb1")

        for job_row in job_rows:
            title = job_row.find("p").text.strip()
            job_url = job_row.find("a")["href"]
            raw_location = job_row.find("div", class_="jv-job-list-location").text
            location = ' '.join(raw_location.split())
            
            if title and job_url:
                jobs.append({"title": title,
                            "location": location,
                            "url": f"https://jobs.jobvite.com{job_url}"})

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
    except json.JSONDecodeError:
        print("Failed to decode JSON response.")
    
    return jobs

if __name__ == "__main__":
    
    all_jobs = {
        "DNEG": fetch_dneg_jobs(),
    }

    for company, job_list in all_jobs.items():
        print(f"\n--- {company} Jobs ---")
        if job_list:
            print(f"Found {len(job_list)} jobs.")
            pprint(job_list)
        else:
            print("No jobs found.")