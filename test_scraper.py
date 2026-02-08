import os
import json
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.job_scraper import JobScraper


def load_studios():
    studios_path = os.path.join(os.path.dirname(__file__), "config", "studios.json")
    with open(studios_path, "r", encoding="utf-8") as f:
        studios = json.load(f)
    return studios


def test_studio(studio_id):
    studios = load_studios()

    # Find the studio
    studio = next((s for s in studios if s["id"] == studio_id), None)

    if not studio:
        print(f"Studio '{studio_id}' not found in studios.json")
        return

    print(f"\n--- Testing Studio: {studio['name']} ({studio['id']}) ---")
    print(f"URL: {studio['careers_url']}")

    scraper = JobScraper()
    jobs = scraper.fetch_jobs(studio)

    print(f"Found {len(jobs)} jobs:")
    for i, job in enumerate(jobs[:10]):
        print(
            f"{i + 1}. {job['title']} | {' '.join(job['location'].split())} | {job['link']} | {job.get('extra_link')}"
        )

    if len(jobs) > 10:
        print(f"... and {len(jobs) - 10} more")


if __name__ == "__main__":
    # CHANGE THE STUDIO ID HERE TO TEST DIFFERENT ONES
    # Options: disney, blur, pixar, ranchito, dreamworks, sony, dneg, illumination,
    #          fortiche, mikros, steamroller, giant, netflix, wildchild, flyingbark,
    #          rodeofx, framestore, skydance, illusorium, littlezoo...

    target_studio = "craftyapes"

    # if len(sys.argv) > 1:
    #     target_studio = sys.argv[1]

    test_studio(target_studio)

    # studios = load_studios()
    # for studio in studios:
    #     print(studio["name"], end=", ")
