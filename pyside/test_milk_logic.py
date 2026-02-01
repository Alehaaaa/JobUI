from bs4 import BeautifulSoup

html = """
<main>
      <article id="post-1534" class="o-content o-content--mtop">
    
<div class="wp-block-columns is-layout-flex wp-container-core-columns-is-layout-1 wp-block-columns-is-layout-flex">
<div class="wp-block-column is-layout-flow wp-block-column-is-layout-flow">
<h1 class="wp-block-heading js-sr">Come Work at Milk!</h1>
</div>
</div>

<h2 class="wp-block-heading js-sr">London</h2>
<div class="c-careers ">
    <div class="c-careers__content">
                    <a href="https://www.milk-vfx.com/?page_id=5408" class="c-career">
                        <span class="c-career__title">Unreal Artist (Mid/Senior) </span>
                    </a> 
                    <a href="https://www.milk-vfx.com/careers/speculative-london/" class="c-career">
                        <span class="c-career__title">Speculative Application</span>
                    </a> 
                    <a href="https://www.milk-vfx.com/careers/interim-finance-director/" class="c-career">
                        <span class="c-career__title">Finance Director (interim)</span>
                    </a> 
            </div>
</div>

<h2 class="wp-block-heading js-sr">Barcelona</h2>
<div class="c-careers ">
    <div class="c-careers__content">
                    <a href="https://www.milk-vfx.com/?page_id=5355" class="c-career">
                        <span class="c-career__title">VFX Line Producer</span>
                    </a> 
                    <a href="https://www.milk-vfx.com/careers/vfx-coordinator-barcelona/" class="c-career">
                        <span class="c-career__title">VFX Coordinator</span>
                    </a> 
                    <a href="https://www.milk-vfx.com/careers/vfx-producer-barcelona/" class="c-career">
                        <span class="c-career__title">VFX Producer </span>
                    </a> 
                    <a href="https://www.milk-vfx.com/careers/speculative-barcelona/" class="c-career">
                        <span class="c-career__title">Speculative Application</span>
                    </a> 
            </div>
</div>

<h2 class="wp-block-heading js-sr">Bordeaux</h2>
<div class="c-careers ">
    <div class="c-careers__content">
                    <a href="https://www.milk-vfx.com/careers/speculative-bordeaux/" class="c-career">
                        <span class="c-career__title">Speculative Application</span>
                    </a> 
            </div>
</div>
</article>
</main>
"""

soup = BeautifulSoup(html, "html.parser")
items = soup.select("div.c-careers__content a")

print(f"Found {len(items)} items")

for item in items:
    title = item.select_one("span.c-career__title").get_text(strip=True)
    location = item.find_previous("h2").get_text(strip=True)
    link = item["href"]
    print(f"{title} | {location} | {link}")
