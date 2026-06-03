# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain
My domain is restaurants in Baltimore. Deciding on where to eat is often not easy and searches for the best restaurants frequently produce long articles or tons and tons of recommendations. Furthermore, finding the perfect restaurant for a specific cuisine or under special conditions (vegan, budget friendly, date night, etc.) is even harder. While this information exists, it is scattered across articles, food reviews, and reddit threads.

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

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
| 12 | The Baltimore Banner| Chef Recommendations| https://www.thebanner.com/culture/food-drink/baltimore-county-chefs-restaurant-recommendations-OCJ2TU5XL5AMXJDWUUFJ2LRLRU/? |
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

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:**

**Overlap:**

**Reasoning:**

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**

**Top-k:**

**Production tradeoff reflection:**

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1.

2.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**
