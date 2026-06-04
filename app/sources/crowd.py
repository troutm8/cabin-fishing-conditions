"""
Crowd-sourced reports - PLACEHOLDER for v1.

Per the plan, crowd-sourced "what's biting" data is the lowest priority and
the hardest to get cleanly (most of it lives in apps and forums with no
friendly API). For version 1 this is a stub so the UI slot exists and the
shape is settled. Wire a real source in here later - for example, scraping a
local shop's report page or pulling a forum/RSS feed - and return a short
text snippet per water id.

Returns a dict keyed by water id, same as the other sources:
  { "pinecrest_lake": {"status": "placeholder",
                       "message": "Sources coming soon"}, ... }
"""


def fetch_all(waters):
    return {
        water["id"]: {"status": "placeholder", "message": "Sources coming soon"}
        for water in waters
    }
