# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->

My domain is restaurants in Baltimore. Deciding on where to eat is often not easy and searches for the best restaurants frequently produce long articles or tons and tons of recommendations. Furthermore, finding the perfect restaurant for a specific cuisine or under special conditions (vegan, budget friendly, date night, etc.) is even harder. While this information exists, it is scattered across articles, food reviews, and reddit threads.

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->


| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | Reddit | Restaurant Recommendations for Chef| https://www.reddit.com/r/baltimore/comments/1e1reaf/restaurant_recommendations_needed_for_my_visiting/ |
| 2 | Reddit | Fine Dining Recommendations| https://www.reddit.com/r/baltimore/comments/1q0mh87/fine_dining_recs/|
| 3 | Reddit | Underrated Restaurants | https://www.reddit.com/r/baltimore/comments/1mp82pl/what_restaurant_in_baltimore_doesnt_get_much_hype/ |
| 4 | Reddit | Best Dinner Spots| https://www.reddit.com/r/baltimore/comments/1tbc2re/best_dinner_spots/|
| 5 | Reddit | Best Restaurants | https://www.reddit.com/r/baltimore/comments/1rl39z1/best_restaurants_in_baltimore/ |
| 6 | Reddit | Mexican Restaurants | https://www.reddit.com/r/baltimore/comments/1tf9p5q/striking_out_on_google_anyone_know_any_mexican/ |
| 7 | Reddit | Dinner with Kids | https://www.reddit.com/r/baltimore/comments/1nekd3b/best_place_to_grab_dinner_with_kids_innear_fells/|
| 8 | Reddit | Jamaican Restaurants | https://www.reddit.com/r/baltimore/comments/1rxh8ur/what_are_the_best_jamaican_restaurants/ |
| 9 | Reddit | Michelin Worthy Restaurants| https://www.reddit.com/r/baltimore/comments/1qomnti/who_are_your_michelin_worthy_restaurants_in_the/|
| 10 | DC Eater| Essential Restaurants| https://dc.eater.com/maps/best-bars-restaurants-bakeries-baltimore-dining-guide-38|
| 11 | Baltimore Magazine | Best Restaurants 2026 | https://www.baltimoremagazine.com/section/fooddrink/best-restaurants-baltimore-2026/ |
| 12 | The Baltimore Banner| Chef Recommendations| https://www.thebanner.com/culture/food-drink/baltimore-county-chefs-restaurant-recommendations-OCJ2TU5XL5AMXJDWUUFJ2LRLRU/ |
| 13 | Like the Tea Eats| Best Restaurants by Neighborhood| https://liketheteaeats.com/best-baltimore-restaurants/ |
| 14 | Baltimore Website| Waterfront Dining | https://baltimore.org/what-to-do/where-to-eat/waterfront-dining-in-baltimore/|
| 15 | Baltimore Website| Best Seafood| https://baltimore.org/what-to-do/where-to-find-baltimores-best-seafood/|
| 16 | Reddit | Seafood | https://www.reddit.com/r/baltimore/comments/18jrk5j/best_seafood_in_town/ |
| 17 | Reddit | Italian | https://www.reddit.com/r/baltimore/comments/1l6evp0/authentic_italian_food/|
| 18 | Reddit | Ethiopian | https://www.reddit.com/r/baltimore/comments/1fzyxf8/ethiopian_recommendations/|
| 19 | Reddit | Asian/Asian Fusion | https://www.reddit.com/r/baltimore/comments/1mifzti/any_good_asianasian_fusion_spots/|
| 20 | Baltimore Website| Asian Owned Restaurants| https://baltimore.org/what-to-do/where-to-eat/asian-owned-restaurants-in-baltimore/|
| 21 | Baltimore Website| Vegan & Vegetarion| https://baltimore.org/what-to-do/vegetarian-vegan-restaurants-in-baltimore/|
| 22 | Baltimore Website| Budget Friendly | https://baltimore.org/what-to-do/where-to-eat/budget-friendly-baltimore-restaurants/|
| 23 | Baltimore Website| International Dining | https://baltimore.org/what-to-do/international-dining-in-baltimore/ |
| 24 | Baltimore Website| Breakfast & Brunch | https://baltimore.org/what-to-do/best-breakfast-and-brunch-spots-in-baltimore/|
| 25 | Baltimore Website| Crab Cakes | https://baltimore.org/what-to-do/where-to-eat/top-eateries-to-enjoy-authentic-baltimore-crab-cakes/|
| 26 | Baltimore Website| Date Night| https://baltimore.org/what-to-do/baltimores-date-night-destinations/|

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:** For articles, the chunk size was targetted to be 450 chars and the cap was 600 chars. For the reddit comments, the chunk size was capped at 1200 chars in order to best keep an entire comment together. If a comment was too long it was split. 

**Overlap:** 75 characters

**Why these choices fit your documents:**
Articles used recursive splitting since each header usually represented a separate review on a different restaurant. The article introduction section was discarded and not chunked because it doesn't include any information about specific restaurants, but because of all the keywords it constantly showed up in retrieval. If a section was longer than 600 chars, it was split on new lines then periods (\n and .). I also included metadata in each chunk with restaurant name, (if present) category, and source. The use of recursive splitting meant that each chunk represented a specific restaurant and its review. The character target fits because restaurant reviews are usually 1-3 paragraphs and a lot of information can be conveyed in just a few sentences. Furthermore, the overlap helps in case chunks do get split, providing context from the previous chunk. 

For the reddit thread, the main idea is to have each comment be its own chunk. This often works because the posts are usually pretty short. I made the character cap much higher for the reddit comments because I found it was better to keep everything from one comment together rather than splitting it up, because splitting often caused too much context to be lost despite having overlap. The original post is its own chunk, and excluded from retrieval since it is just asking questions/recommendations. 

**Final chunk count:** 978

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:** all-MiniLM-L6-v2

**Production tradeoff reflection:** If cost were not a constraint, I would weigh several tradeoffs before changing models. Domain-specific accuracy matters most for this project and cuisine terms are easy for a general-purpose model to conflate. Therefore, a stronger embedder (e.g. OpenAI text-embedding-3-large or a domain-finetuned model) could improve retrieval on compound queries like “Hampden brunch.” Context length is less critical here because chunks are capped at ~450–600 characters, but a longer-context model would help if we moved to whole-article or multi-comment embedding. For the tradeoffs: all-MiniLM-L6-v2 runs locally via sentence-transformers with no API dependency and fast inference. On the other hand, an API-hosted model adds network latency and uptime risk but scales better as the index grows.  


---

## Grounded Generation

**System prompt grounding instruction:**

The system prompt uses mandatory language (MUST / MUST NOT):


You are a Baltimore restaurant guide assistant. You MUST answer using ONLY the information
in the user's provided documents. You MUST NOT use any outside knowledge. If the documents
name restaurants or describe dining options relevant to the question, you MUST recommend
them using details from the documents. Only if the documents contain NO relevant information,
respond with exactly: "I don't have enough information on that." Do not invent restaurant
names, addresses, or details not present in the documents. Do not include source citations
in your answer — sources are handled separately. Be concise and helpful.

Structural guardrails beyond the prompt:
- Retrieved chunks are formatted as numbered [Document N] blocks with source name and text
- If retrieve() returns zero chunks, the LLM is not called and the insufficient-info message is returned immediately.
- Groq llama-3.3-70b-versatile runs at temperature=0 to reduce creative drift.
- Category-aware retrieval filters chunks by query keywords (budget, Ethiopian, family, etc.) before generation.

**How source attribution is surfaced in the response:**

Sources are built by build_sources() from chunk metadata (source, url, type, restaurant) and not parsed from the LLM answer. The Gradio UI displays them in a separate "Retrieved from" textbox, one bullet per source with URL and restaurants mentioned in the retrieved chunks. This guarantees citations match what was actually retrieved, even if the LLM omits or misstates a source name.

---

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | Where can I get the best crab cakes in Baltimore? | Faidley's, LP Steamers, Thames Street Oyster House from sources #25, #16 | Recommended Koco's Pub, Gertrude's Chesapeake Kitchen, Phillips Seafood, Land of Kush from Baltimore.org Crab Cakes (#25). All names and details trace to retrieved chunks. | Relevant | Accurate |
| 2 | What are some good restaurants in Baltimore for a date night? | Date night source (#26) and fine dining Reddit (#2); Charleston, Cinghiale, Food Market | Recommended The Elk Room, Petit Louis Bistro, Topside at Hotel Revival from Baltimore.org Date Night (#26). | Relevant | Accurate |
| 3 | Where can I find good budget-friendly dinner food in Baltimore? | Mostly Source #22, Ekiben, Empanada Lady, Johnny Rad's, Little Donna's | Recommended Tagliata, The Outpost, Thames Street Oyster House, The Dive from Baltimore.org — Budget Friendly (#22). Grounded but missed Ekiben/Johnny Rad's because those chunks ranked lower in retrieval. | Partially relevant | Accurate |
| 4 | What are the best Ethiopian restaurants in Baltimore? | Source #18, Dukem, Lalibela, etc. | Recommended Ma'aed and Dukem with details from Reddit Ethiopian thread (#18). All claims trace to retrieved chunk text. | Relevant | Accurate |
| 5 | What's a good family-friendly restaurant near Fells Point for dinner with kids? | Source #7, Koopers, Alexander's Tavern, Broadway Market | Recommended Broadway Market, Nanami, Koopers, Bunnies, Chilangos from Dinner with Kids thread (#7). All names appear in retrieved Reddit comments. | Relevant | Accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

**Out-of-domain grounding test:** I asked the question "What are the best sushi restaurants in Tokyo?" 
The system responded with "I don't have enough information on that." despite retrieving unrelated Baltimore Asian-restaurant chunks. This is the correct response  since there is no information about restaurants in Tokyo. The system should not respond with restaurants in Baltimore or hallucinate and make up restaurants. 

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:** Which restaurants in Hampden are good for brunch?

**What the system returned:** I don't have enough information on that.

**Root cause (tied to a specific pipeline stage):** Retrieval failure is the primary cause. There exists several chunks that contain information about brunch spots in Hampden, but the retrieval first searches for brunch places and then checks if they mention Hampden. All 5 retrieved chunks come from the Baltimore.org Breakfast & Brunch article which actually does contain a restaurant in Hampden, but never explicitly states Hampden. Therefore, the model is unable to recognize any restaurant that fits both brunch and hampden. 

Interesting side note: when I changed the question to "Which restaurants near Hampden are good for brunch?" The model responded several times with "I don't have enough information on that." but sometimes it actually was able to recommend me restaurants near Hampden. 

**What you would change to fix it:** One way to fix retrival when multiple categories are detected is to not let the first category consume all 5 slots. I could find 2-3 chunks for brunch and 2-3 for the specific neighborhood. Then chunks that specifically mention hampden will surface, instead of those only mentioning brunch. 

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:** The spec helped me map out and understand each step of the process. During implementiation, it helped because I could continuously reference it for guidance, as well as provide it as a resource for the AI tool.

**One way your implementation diverged from the spec, and why:** I think one way my implementation diverged from the spec was with the chunking part. Originally, I thought it would be way more simple, but I quickly ran into a lot of issues with the quality of my chunks. I made several edits and through many iterations (and lots of talking to Claude), I altered the chunking strategy I had for the Reddit threads, metadata inclusion, and what information was actually relevant and needed to be chunked. 



---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1:** Ingestion

- *What I gave the AI:* I gave the AI my planning.md file as well as my goals to scrape information from the documents
- *What it produced:* The AI successfully produced scrape.py which was able to get the information from the articles and store them as txt files. 
- *What I changed or overrode:* The AI was unable to access the Reddit threads, so I had to manually save them as json files into the raw folder and then the AI was able to turn those files into txt files. 

**Instance 2:** Chunking

- *What I gave the AI:* I gave the AI my planning.md file
- *What it produced:* It chunked the documents
- *What I changed or overrode:* I noticed there were a lot of issues with the chunks. Reddit chunks were splitting early and losing a lot of context, overlap wasn't working properly, the metadata wasn't always correct. I changed the methods a bit to make each Reddit comment its own chunk, fixed the overlap issue, and used some filtering to get the correct restaurant name, or set it as null if no name was found. 
